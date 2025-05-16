using JuMP # building models
using DataStructures # using dictionaries with a default value
using HiGHS # solver for the JuMP model
using CSV # readin of CSV files
using DataFrames # data tables
using Statistics # mean function
using Plots  # generate graphs
using Plots.Measures
using StatsPlots # additional features for plots
include(joinpath(@__DIR__, "colors.jl")) # colors for the plots

### some helper functions ###
# read the csv files
readcsv(x; dir=@__DIR__) = CSV.read(joinpath(dir, x), DataFrame, stringtype=String)
# readin function for parameters; this makes handling easier
readin(x::AbstractDataFrame; default=0,dims=1) = DefaultDict(default,Dict((dims > 1 ? Tuple(row[y] for y in 1:dims) : row[1]) => row[dims+1] for row in eachrow(x)))
readin(x::AbstractString; dir=@__DIR__, kwargs...) = readin(readcsv(x, dir=dir); kwargs...)

### Read in of parameters ###
# We define our sets from the csv files
technologies = readcsv("technologies.csv").technology
fuels = readcsv("fuels.csv").fuel
# now we also want to define a set called "hour"
hour = 1:120
# and we want to know the number of elements
elements = length(hour)

# Also, we read our input parameters via csv files
Demand = readin("demand.csv", dims=1)
OutputRatio = readin("outputratio.csv", dims=2)
InputRatio = readin("inputratio.csv", dims=2)
VariableCost = readin("variablecost.csv", dims=1)
InvestmentCost = readin("investmentcost.csv", dims=1)
EmissionRatio = readin("emissionratio.csv", dims=1)
# also read in DemandProfile, CapacityFactor, and TagDispatchableTechnology
CapacityFactor = readin("capacity_factors_2015.csv",dims=2,default=0)
TagDispatchableTechnology = readin("tagdispatchabletechnology.csv",dims=1)
DemandProfile = readin("demandprofile.csv",dims=2,default=1/elements)

# we need to ensure that all non-variable technologies do have a CapacityFactor of 1 at all times
for t in technologies
    if TagDispatchableTechnology[t] > 0
        for h in hour
            CapacityFactor[h,t] = 1
        end
    end
end

# we can test if solar does still produce during the night
CapacityFactor[4,"SolarPV"]
CapacityFactor[2,"CoalMine"]

# our emission limit
EmissionLimit = 5000

# define the dictionary for max capacities with specific default value
MaxCapacity = readin("maxcapacity.csv", default=999, dims=1)

### building the model ###
# instantiate a model with an optimizer
ESM = Model(HiGHS.Optimizer)

# what variables need to be time-dependent? you need to change them! -> same goes for all equations below

# this creates our variables
@variable(ESM, TotalCost[technologies] >= 0)
@variable(ESM, FuelProductionByTechnology[hour, technologies, fuels] >= 0)
@variable(ESM, Capacity[technologies] >=0)
@variable(ESM, FuelUseByTechnology[hour, technologies, fuels] >=0)
@variable(ESM, TechnologyEmissions[technologies] >=0)
@variable(ESM, Curtailment[hour, fuels]>=0)

## constraints ##
# Generation must meet demand
@constraint(ESM, EnergyBalance[h in hour, f in fuels],
    sum(FuelProductionByTechnology[h, t,f] for t in technologies) - Curtailment[h, f] == 
    Demand[f]*DemandProfile[h, f] + sum(FuelUseByTechnology[h,t,f] for t in technologies)
)

# calculate the total cost
@constraint(ESM, ProductionCost[t in technologies],
    sum(FuelProductionByTechnology[h,t,f] for h in hour, f in fuels) 
    * VariableCost[t] + Capacity[t] * InvestmentCost[t] == TotalCost[t]
)

# limit the production by the installed capacity
@constraint(ESM, ProductionFuntion[h in hour, t in technologies, f in fuels,
                                                    ;TagDispatchableTechnology[t]==1],
    OutputRatio[t,f] * Capacity[t] * CapacityFactor[h,t] 
    >= FuelProductionByTechnology[h,t,f]
)


@constraint(ESM, ProductionFuntion_RES[h in hour, t in technologies, f in fuels,
                                                    ;TagDispatchableTechnology[t]==0],
    OutputRatio[t,f] * Capacity[t] * CapacityFactor[h,t] 
    == FuelProductionByTechnology[h,t,f]
)

# define the use by the production
@constraint(ESM, UseFunction[h in hour, t in technologies, f in fuels],
    InputRatio[t,f] * sum(FuelProductionByTechnology[h,t,ff] for ff in fuels) 
    == FuelUseByTechnology[h,t,f]
)

# define the emissions
@constraint(ESM, TechnologyEmissionFunction[t in technologies],
    sum(FuelProductionByTechnology[h,t,f] for h in hour, f in fuels) * EmissionRatio[t] 
    == TechnologyEmissions[t]
)

# limit the emissions
@constraint(ESM, TotalEmissionsFunction,
    sum(TechnologyEmissions[t] for t in technologies) <= EmissionLimit
)

# installed capacity is limited by the maximum capacity
@constraint(ESM, MaxCapacityFunction[t in technologies],
     Capacity[t] <= MaxCapacity[t]
)

# the objective function
# total costs should be minimized
@objective(ESM, Min, sum(TotalCost[t] for t in technologies))

# this starts the optimization
# the assigned solver (here HiGHS) will takes care of the solution algorithm
optimize!(ESM)
# reading our objective value
objective_value(ESM)

# some result analysis
value.(FuelProductionByTechnology)
value.(Capacity)

df_res_production = DataFrame(Containers.rowtable(value,FuelProductionByTechnology; header = [:Hour, :Technology, :Fuel, :value]))
df_res_capacity = DataFrame(Containers.rowtable(value,Capacity; header = [:Technology, :value]))

transform!(df_res_production, "Technology" => ByRow(x-> colors[x]) => "Color")
transform!(df_res_capacity, "Technology" => ByRow(x-> colors[x]) => "Color")

# and some plots
groupedbar(
    df_res_production.Fuel,
    df_res_production.value,
    group=df_res_production.Technology,
    bar_position=:stack,
    title="Production by Technology",
    linewidth=0,
    color=df_res_production.Color,
    legend=false
)

bar(
    df_res_capacity.Technology,
    df_res_capacity.value,
    title="Installed Capacity by Technology",
    color=df_res_capacity.Color,
    linewidth=0,
    rotation=90
)

gdf_production_by_fuel = groupby(df_res_production, :Fuel)
n_fuels = length(gdf_production_by_fuel)
plts = map(enumerate(pairs(gdf_production_by_fuel))) do (i,(k,v))
    p = groupedbar(
        v.Hour,
        v.value,
        group=v.Technology,
        bar_position=:stack,
        title="$(k[1])",
        linewidth=0,
        color=v.Color,
        legend=i == n_fuels ? (0.15,-0.5) : false,
        bottom_margin=i == n_fuels ? 15mm : 2mm,
        legend_column=5
    )

    d = [Demand[k[1]]*DemandProfile[h,k[1]] for h in hour]
    u = sum(value.(FuelUseByTechnology)[:,t, k[1]] for t in technologies)
    du = d .+ u.data
    plot!(p, hour, d, color=:black, linewidth=2, label="Demand")
    plot!(p, hour, du, color=:black, linestyle=:dash, linewidth=2, label="Demand + Use")

    return p
end

plot(plts..., layout=(n_fuels,1), size=(1200,1200))

sum(value.(Curtailment))
Demand["Power"]