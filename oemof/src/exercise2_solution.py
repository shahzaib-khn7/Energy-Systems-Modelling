#%% Load libaries
from oemof import solph
from oemof.tools import economics

import pandas as pd
import matplotlib.pyplot as plt
import pprint as pp
from collections import OrderedDict

#%% Read input data
# Input Data Reading
timeseries = pd.read_excel('../data/input_data_exercise2.xls', 
                           sheet_name='timeseries', 
                           index_col=[0], 
                           parse_dates=True)

# Add timestep (oemof model needs time increment)
timeseries.index.freq = '1H'

capacities = pd.read_excel('../data/input_data_exercise2.xls', 
                           sheet_name='capacity', 
                           index_col=[0], 
                           parse_dates=True)
tech = pd.read_excel('../data/input_data_exercise2.xls', 
                           sheet_name='tech', 
                           index_col=[0], 
                           parse_dates=True)
costs = pd.read_excel('../data/input_data_exercise2.xls', 
                           sheet_name='costs', 
                           index_col=[0], 
                           parse_dates=True)

#%% Initialize the energy system and read/calculate necessary parameters
energysystem = solph.EnergySystem(timeindex=timeseries.index)

#%% Create oemof Buses
# create electricity bus
bus_electricity = solph.Bus(label='bus_electricity_l')
# create heat bus
bus_heat = solph.Bus(label='bus_heat_l')
# create biomass bus
bus_biomass = solph.Bus(label='bus_biomass_l')

# add buses to energy model
energysystem.add(bus_electricity, bus_heat, bus_biomass)

#%% Create oemof Sinks
# create excess component for the electricity bus to allow overproduction
electricity_excess = solph.Sink(label='electricty_excess_l', 
                                inputs={bus_electricity: solph.Flow()})

# create simple sink object representing the electrical demand
electricity_demand = solph.Sink(label='electricity_demand_l',
                                inputs={bus_electricity: solph.Flow(
                                        fix=timeseries['electricity'], 
                                        nominal_value=capacities['electricity']['amount'])
                                        })

# create excess component for the heat bus to allow overproduction
heat_excess = solph.Sink(label='heat_excess_l', 
                         inputs={bus_heat: solph.Flow()})

# create simple sink object representing the heat demand (space heat and hot water demand)
heat_space_demand = solph.Sink(label='heat_space_demand_l',
                               inputs={bus_heat: solph.Flow(
                                       fix=timeseries['space_heat'], 
                                       nominal_value=capacities['space_heat']['amount'])},)

heat_dhw_demand = solph.Sink(label='heat_dhw_demand_l',
                             inputs={bus_heat: solph.Flow(
                                 fix=timeseries['dhw_heat'], 
                                 nominal_value=capacities['dhw_heat']['amount'])},)

#energysystem.add(electricity_excess, electricity_demand,
#                 heat_excess, heat_space_demand, heat_dhw_demand)
#%% Economic caluclation (for dispatch/sizing optimization) 

## Capital costs
# Annuities
a_onshore = economics.annuity(capex=costs['onshore']['capex'], 
                              n=costs['onshore']['lifetime'],
                              wacc=costs['onshore']['wacc'])
a_offshore = economics.annuity(capex=costs['offshore']['capex'], 
                               n=costs['offshore']['lifetime'],
                               wacc=costs['offshore']['wacc'])
a_pv = economics.annuity(capex=costs['pv']['capex'], 
                         n=costs['pv']['lifetime'],
                         wacc=costs['pv']['wacc'])
a_ror = economics.annuity(capex=costs['ror']['capex'], 
                          n=costs['ror']['lifetime'],
                          wacc=costs['ror']['wacc'])

a_chp = economics.annuity(capex=costs['chp']['capex'], 
                            n=costs['chp']['lifetime'],
                            wacc=costs['chp']['wacc'])
a_hp = economics.annuity(capex=costs['hp']['capex'], 
                           n=costs['hp']['lifetime'],
                           wacc=costs['hp']['wacc'])

a_battery_energy = economics.annuity(capex=costs['battery']['capex_energy'], 
                                     n=costs['battery']['lifetime'],
                                     wacc=costs['battery']['wacc'])
a_battery = economics.annuity(capex=costs['battery']['capex'], 
                              n=costs['battery']['lifetime'],
                              wacc=costs['battery']['wacc'])
a_hydrogen_energy = economics.annuity(capex=costs['hydrogen']['capex_energy'], 
                                      n=costs['hydrogen']['lifetime'],
                                      wacc=costs['hydrogen']['wacc'])
a_hydrogen = economics.annuity(capex=costs['hydrogen']['capex'], 
                               n=costs['hydrogen']['lifetime'],
                               wacc=costs['hydrogen']['wacc'])
a_acaes_energy = economics.annuity(capex=costs['acaes']['capex_energy'], 
                                     n=costs['acaes']['lifetime'],
                                     wacc=costs['acaes']['wacc'])
a_acaes = economics.annuity(capex=costs['acaes']['capex'], 
                              n=costs['acaes']['lifetime'],
                              wacc=costs['acaes']['wacc'])
a_tes_energy = economics.annuity(capex=costs['tes']['capex_energy'], 
                                   n=costs['tes']['lifetime'],
                                       wacc=costs['tes']['wacc'])


# Capital costs
cc_onshore = (a_onshore + costs['onshore']['fom'])
cc_offshore = (a_offshore + costs['offshore']['fom'])
cc_pv = (a_pv + costs['pv']['fom'])
cc_ror = (a_ror + costs['ror']['fom'])

cc_chp = (a_chp + costs['chp']['fom'])
cc_hp = (a_hp + costs['hp']['fom'])

cc_battery_energy = (a_battery_energy + costs['battery']['fom'])
cc_battery = (a_battery)
cc_hydrogen_energy = (a_hydrogen_energy + costs['hydrogen']['fom'])
cc_hydrogen = (a_hydrogen)
cc_acaes_energy = (a_acaes_energy + costs['acaes']['fom'])
cc_acaes = (a_acaes)
cc_tes_energy = (a_tes_energy + costs['tes']['fom'])


## Marginal costs
mc_onshore = costs['onshore']['vom']
mc_offshore = costs['offshore']['vom']
mc_pv = costs['pv']['vom']
mc_ror = costs['ror']['vom']

mc_chp = costs['chp']['vom']
mc_hp = costs['hp']['vom']

mc_battery = costs['battery']['vom']
mc_hydrogen = costs['hydrogen']['vom']
mc_acaes = costs['acaes']['vom']
mc_tes = costs['tes']['vom']

#%%Create oemof Sources

# create fixed source object representing wind power plants offshore
wind_offshore = solph.Source(label='wind_offshore_l',
                             outputs={bus_electricity: solph.Flow(   
                                     fix=timeseries['offshore'], 
                                     variable_costs=mc_offshore,
                                     investment=solph.Investment(
                                                ep_costs=cc_offshore,
                                                maximum=capacities['offshore']['capacity_potential'],
                                                existing=capacities['offshore']['capacity_existing']))
                                    },)

# create fixed source object representing wind power plants onshore
wind_onshore = solph.Source(label='wind_onshore_l',
                            outputs={bus_electricity: solph.Flow(
                                    fix=timeseries['onshore'], 
                                    variable_costs=mc_onshore,
                                    investment=solph.Investment(
                                               ep_costs=cc_onshore,
                                               maximum=capacities['onshore']['capacity_potential'],
                                               existing=capacities['onshore']['capacity_existing']))
                                    },)

# create fixed source object representing pv power plants
pv = solph.Source(label='pv_l',
                  outputs={bus_electricity: solph.Flow(
                           fix=timeseries['pv'], 
                           variable_costs=mc_pv,
                           investment=solph.Investment(
                                      ep_costs=cc_pv,
                                      maximum=capacities['pv']['capacity_potential'],
                                      existing=capacities['pv']['capacity_existing']))
                           },)

# create fixed source object representing hydro run of river plant
ror = solph.Source(label='ror_l',
                   outputs={bus_electricity: solph.Flow(
                            fix=timeseries['ror'], 
                            variable_costs=mc_ror,
                            investment=solph.Investment(
                                       ep_costs=cc_ror,
                                       maximum=capacities['ror']['capacity_potential'],
                                       existing=capacities['ror']['capacity_existing']))
                            },)

# create fixed source object representing biomass ressource
biomass = solph.Source(label='biomass_l',
                       outputs={bus_biomass: solph.Flow(
                               nominal_value=capacities['biomass']['capacity_potential'],
                               summed_max=1)
                       },)
                                   	
#%% Create oemof Storages

# create storage object representing a battery
battery = solph.components.GenericStorage(label='battery_l',
                                          inputs={bus_electricity: solph.Flow(
                                                  investment=solph.Investment(
                                                             ep_costs=cc_battery,
                                                             maximum=capacities['battery']['storage_power_potential']),
                                                  variable_costs=mc_battery)},
                                          outputs={bus_electricity: solph.Flow()},
                                          loss_rate=tech['battery']['loss'],
                                          initial_storage_level=0,
                                          invest_relation_input_capacity=1/tech['battery']['max_hours'],
                                          invest_relation_output_capacity=1/tech['battery']['max_hours'],
                                          inflow_conversion_factor=1,
                                          outflow_conversion_factor=tech['battery']['efficiency'],
                                          investment=solph.Investment(
                                                     ep_costs=cc_battery_energy,
                                                     maximum=capacities['battery']['capacity_potential']),)

# create storage object representing a hydrogen
hydrogen = solph.components.GenericStorage(label='hydrogen_l',
                                          inputs={bus_electricity: solph.Flow(
                                                  investment=solph.Investment(
                                                             ep_costs=cc_hydrogen,
                                                             maximum=capacities['hydrogen']['storage_power_potential']),
                                                  variable_costs=mc_hydrogen)},
                                          outputs={bus_electricity: solph.Flow()},
                                          loss_rate=tech['hydrogen']['loss'],
                                          initial_storage_level=0,
                                          invest_relation_input_capacity=1/tech['hydrogen']['max_hours'],
                                          invest_relation_output_capacity=1/tech['hydrogen']['max_hours'],
                                          inflow_conversion_factor=1,
                                          outflow_conversion_factor=tech['hydrogen']['efficiency'],
                                          investment=solph.Investment(
                                                     ep_costs=cc_hydrogen_energy,
                                                     maximum=capacities['hydrogen']['capacity_potential']),)

# create storage object representing a adiabatic compressed air energy storage (ACAES)
acaes = solph.components.GenericStorage(label='acaes_l',
                                          inputs={bus_electricity: solph.Flow(
                                                  investment=solph.Investment(
                                                             ep_costs=cc_acaes,
                                                             maximum=capacities['acaes']['storage_power_potential']),
                                                  variable_costs=mc_acaes)},
                                          outputs={bus_electricity: solph.Flow()},
                                          loss_rate=tech['acaes']['loss'],
                                          initial_storage_level=0,
                                          invest_relation_input_capacity=1/tech['acaes']['max_hours'],
                                          invest_relation_output_capacity=1/tech['acaes']['max_hours'],
                                          inflow_conversion_factor=1,
                                          outflow_conversion_factor=tech['acaes']['efficiency'],
                                          investment=solph.Investment(
                                                     ep_costs=cc_acaes_energy,
                                                     maximum=capacities['acaes']['capacity_potential']),)

# create storage object representing a battery
tes = solph.components.GenericStorage(label='tes_l',
                                          inputs={bus_heat: solph.Flow(
                                                  investment=solph.Investment(
                                                             maximum=capacities['tes']['storage_power_potential']),
                                                  variable_costs=mc_tes)},
                                          outputs={bus_heat: solph.Flow()},
                                          loss_rate=tech['tes']['loss'],
                                          initial_storage_level=0,
                                          invest_relation_input_capacity=1/tech['tes']['max_hours'],
                                          invest_relation_output_capacity=1/tech['tes']['max_hours'],
                                          inflow_conversion_factor=1,
                                          outflow_conversion_factor=tech['tes']['efficiency'],
                                          investment=solph.Investment(
                                                     ep_costs=cc_tes_energy,
                                                     maximum=capacities['tes']['capacity_potential']),)

#%% Create oemof Transformers

# create transformer object representing heat pumps
hp = solph.Transformer(label='hp_l',
                              inputs={bus_electricity: solph.Flow()},
                              outputs={bus_heat: solph.Flow(
                                       investment=solph.Investment(
                                                  ep_costs=cc_hp),
                                       variable_costs=mc_hp)},
                              conversion_factors={bus_electricity: 1/tech['hp']['efficiency']},
                              )

# create transformer object representing CHP plants
chp = solph.Transformer(label='chp_l',
                        inputs={bus_biomass: solph.Flow(
                                    variable_costs=mc_chp)},
                        outputs={bus_electricity: solph.Flow(
                                    investment=solph.Investment(
                                               ep_costs=cc_chp,
                                               existing=capacities['chp']['capacity_existing'])),
                                 bus_heat: solph.Flow()},
                        conversion_factors={bus_electricity: tech['chp']['electric_efficiency'],
                                            bus_heat: tech['chp']['thermal_efficiency']},
                        )

#%% Add all components to the energysystem
energysystem.add(electricity_excess, electricity_demand,
                 heat_excess, heat_space_demand, heat_dhw_demand,
                 wind_offshore, wind_onshore, pv, ror, biomass,
                 battery, hydrogen, acaes, tes, 
                 hp, chp)

#%% Optimise the energy system
# initialise the operational model
om = solph.Model(energysystem)
om.solve(solver='cbc')

#Extract main results save results to dump (optional)
energysystem.results['main'] = solph.processing.results(om)
energysystem.dump('../results/dumps',
                  filename='model.oemof')

#%% Extract results 

# Extract results dict
results = solph.processing.results(om)

# Extract component results
results_wind_offshore = solph.views.node(results, 'wind_offshore_l')
results_wind_onshore = solph.views.node(results, 'wind_onshore_l')
results_pv = solph.views.node(results, 'pv_l')
results_ror = solph.views.node(results, 'ror_l')

results_biomass = solph.views.node(results, 'bus_biomass_l')
results_chp = solph.views.node(results, 'chp_l')
results_hp = solph.views.node(results, 'hp_l')

results_battery = solph.views.node(results, 'battery_l')
results_hydrogen = solph.views.node(results, 'hydrogen_l')
results_acaes = solph.views.node(results, 'acaes_l')
results_tes = solph.views.node(results, 'tes_l')

# Extract bus results
results_electricity_bus = solph.views.node(results, 'bus_electricity_l')
results_heat_bus = solph.views.node(results, 'bus_heat_l')
results_biomass_bus = solph.views.node(results, 'bus_biomass_l')

#%% Results: Installed capacities
# Define capacity results dict
results_capacity = OrderedDict()

# installed capacity of wind power plant in MW
results_capacity['wind_onshore_invest_MW'] = results[(wind_onshore, bus_electricity)]['scalars']['invest']
# installed capacity of wind power plant in MW
results_capacity['wind_offshore_invest_MW'] = results[(wind_offshore, bus_electricity)]['scalars']['invest']
# installed capacity of pv power plant in MW
results_capacity['pv_invest_MW'] = results[(pv, bus_electricity)]['scalars']['invest']
# installed capacity of pv power plant in MW
results_capacity['ror_invest_MW'] = results[(ror, bus_electricity)]['scalars']['invest']

# installed capacity of chp plant in MW
results_capacity['chp_invest_MW_el'] = results[(chp, bus_electricity)]['scalars']['invest']
# installed capacity of heat pump in MW
results_capacity['hp_invest_MW_th'] = results[(hp, bus_heat)]['scalars']['invest']

# installed capacity of battery storage in MWh
results_capacity['battery_invest_MWh'] = results[(battery, None)]['scalars']['invest']
# installed power capacity of battery storage in MW
results_capacity['battery_invest_MW_ch'] = results[(bus_electricity, battery)]['scalars']['invest']
results_capacity['battery_invest_MW_dch'] = results[(battery, bus_electricity)]['scalars']['invest']

# installed capacity of hydrogen storage in MWh
results_capacity['hydrogen_invest_MWh'] = results[(hydrogen, None)]['scalars']['invest']
# installed power capacity of hydrogen storage in MW
results_capacity['hydrogen_invest_MW_ch'] = results[(bus_electricity, hydrogen)]['scalars']['invest']
results_capacity['hydrogen_invest_MW_dch'] = results[(hydrogen, bus_electricity,)]['scalars']['invest']

# installed capacity of acaes storage in MWh
results_capacity['acaes_invest_MWh'] = results[(acaes, None)]['scalars']['invest']
# installed power capacity of acaes storage in MW
results_capacity['acaes_invest_MW_ch'] = results[(bus_electricity, acaes)]['scalars']['invest']
results_capacity['acaes_invest_MW_dch'] = results[(acaes, bus_electricity)]['scalars']['invest']

# installed capacity of thermal storage in MWh
results_capacity['thermal_storage_invest_MWh'] = results[(tes, None)]['scalars']['invest']
# installed power capacity of thermal storage in MW
results_capacity['thermal_storage_invest_MW_ch'] = results[(bus_heat, tes)]['scalars']['invest']
results_capacity['thermal_storage_invest_MW_dch'] = results[(tes, bus_heat)]['scalars']['invest']

pp.pprint(results_capacity)

# Transfer dict to DataFRame and transpose for better readybility
results_capacity_df = pd.DataFrame(results_capacity, index=[0]).T

#%% Results: Investment costs

## Investment costs
results_inv_costs = OrderedDict()
# Wind onshore
results_inv_costs['wind_onshore_mio'] = round(a_onshore * results_capacity['wind_onshore_invest_MW'] /1e6, 2)
# Wind offshore
results_inv_costs['wind_offshore_mio'] = round(a_offshore * results_capacity['wind_offshore_invest_MW'] /1e6, 2)
# PV
results_inv_costs['pv_mio'] = round(a_pv * results_capacity['pv_invest_MW'] /1e6, 2)
# RoR
results_inv_costs['ror_mio'] = round(a_ror * results_capacity['ror_invest_MW'] /1e6, 2)
# chp
results_inv_costs['chp_mio'] = round(a_chp * results_capacity['chp_invest_MW_el'] /1e6, 2)
# hp
results_inv_costs['hp_mio'] = round(a_hp * results_capacity['hp_invest_MW_th'] /1e6, 2)

# battery
results_inv_costs['battery_mio'] = round(a_battery_energy * results_capacity['battery_invest_MWh'] /1e6, 2)
results_inv_costs['battery_power_ch_mio'] = round(a_battery * results_capacity['battery_invest_MW_ch'] /1e6, 2)
results_inv_costs['battery_power_dch_mio'] = round(a_battery * results_capacity['battery_invest_MW_dch'] /1e6, 2)
# hydrogen
results_inv_costs['hydrogen_mio'] = round(a_hydrogen_energy * results_capacity['hydrogen_invest_MWh'] /1e6, 2)
results_inv_costs['hydrogen_power_ch_mio'] = round(a_hydrogen * results_capacity['hydrogen_invest_MW_ch'] /1e6, 2)
results_inv_costs['hydrogen_power_dch_mio'] = round(a_hydrogen * results_capacity['hydrogen_invest_MW_dch'] /1e6, 2)
# acaes
results_inv_costs['acaes_mio'] = round(a_acaes_energy * results_capacity['acaes_invest_MWh'] /1e6, 2)
results_inv_costs['acaes_power_ch_mio'] = round(a_acaes * results_capacity['acaes_invest_MW_ch'] /1e6, 2)
results_inv_costs['acaes_power_dch_mio'] = round(a_acaes * results_capacity['acaes_invest_MW_dch'] /1e6, 2)
# tes
results_inv_costs['tes_mio'] = round(a_tes_energy * results_capacity['thermal_storage_invest_MWh'] /1e6, 2)

# Total
results_inv_costs['total'] = sum(results_inv_costs.values())

pp.pprint(results_inv_costs)

# Transfer dict to DataFRame and transpose for better readybility
results_inv_costs_df = pd.DataFrame(results_inv_costs, index=[0]).T


## Variable costs
#wind_offshore_variable = [b for a, b in om.flows.items() if a[0] == wind_offshore][0].variable_costs
#battery_variable = [b for a, b in om.flows.items() if a[0] == battery][0].variable_costs
#chp_variable = [b for a, b in om.flows.items() if a[0] == chp][0].variable_costs

#%% Results: Biomass, Heat and electricty generation mix in TWh
results_energy_biomass = OrderedDict()
results_energy_biomass['total_TWh'] = results_chp['sequences'][(('bus_biomass_l', 'chp_l'), 'flow')].sum() / 1e6
pp.pprint(results_energy_biomass)

results_energy_heat = OrderedDict()
results_energy_heat['chp_TWh'] = results_chp['sequences'][('chp_l','bus_heat_l'),'flow'].sum() / 1e6
results_energy_heat['hp_TWh'] = results_hp['sequences'][('hp_l','bus_heat_l'),'flow'].sum() / 1e6
results_energy_heat['total_TWh'] = sum(results_energy_heat.values())
pp.pprint(results_energy_heat)

results_energy_electricity = OrderedDict()
results_energy_electricity['wind_onshore_TWh'] = results_wind_onshore['sequences'][('wind_onshore_l','bus_electricity_l'),'flow'].sum() / 1e6
results_energy_electricity['wind_offshore_TWh'] = results_wind_offshore['sequences'][('wind_offshore_l','bus_electricity_l'),'flow'].sum() / 1e6
results_energy_electricity['pv_TWh'] = results_pv['sequences'][('pv_l','bus_electricity_l'),'flow'].sum() / 1e6
results_energy_electricity['ror_TWh'] = results_ror['sequences'][('ror_l','bus_electricity_l'),'flow'].sum() / 1e6
results_energy_electricity['chp_TWh'] = results_chp['sequences'][('chp_l','bus_electricity_l'),'flow'].sum() / 1e6
results_energy_electricity['total_TWh'] = sum(results_energy_electricity.values())

pp.pprint(results_energy_electricity)

# Transfer dict to DataFrame and transpose for better readybility
results_energy_biomass_df = pd.DataFrame(results_energy_biomass, index=[0]).T
results_energy_heat_df = pd.DataFrame(results_energy_heat, index=[0]).T
results_energy_electricity_df = pd.DataFrame(results_energy_electricity, index=[0]).T

#%% Results: Collection of all results and exporting to ecxel file

# Create a Pandas Excel writer using XlsxWriter as the engine.
with pd.ExcelWriter('../results/results_overview.xlsx', engine='xlsxwriter') as writer:  
    
    # Write each dataframe to a different worksheet.
    results_capacity_df.to_excel(writer, sheet_name='capacities')
    results_energy_biomass_df.to_excel(writer, sheet_name='energy_biomass')
    results_energy_heat_df.to_excel(writer, sheet_name='energy_heat')
    results_energy_electricity_df.to_excel(writer, sheet_name='energy_elec')
    results_inv_costs_df.to_excel(writer, sheet_name='inv_costs')


#%% Results: Extract results to plot

results_elec_ts = OrderedDict()
# Extract electricty component timeseries
results_elec_ts['wind_offshore'] = results[(wind_offshore, bus_electricity)]['sequences']['flow']
results_elec_ts['wind_onshore'] = results[(wind_onshore, bus_electricity)]['sequences']['flow'] 
results_elec_ts['pv'] = results[(pv, bus_electricity)]['sequences']['flow']
results_elec_ts['ror'] = results[(ror, bus_electricity)]['sequences']['flow']
results_elec_ts['chp'] = results[(chp, bus_electricity)]['sequences']['flow']

results_elec_ts['elec_demand'] = results[(bus_electricity, electricity_demand)]['sequences']['flow']
results_elec_ts['elec_excess'] = results[(bus_electricity, electricity_excess)]['sequences']['flow']


results_heat_ts = OrderedDict()
# Extract results to plot
results_heat_ts['hp'] = results[(hp, bus_heat)]['sequences']['flow']
results_heat_ts['chp'] = results[(chp, bus_heat)]['sequences']['flow']

results_heat_ts['heat_dhw_demand'] = solph.views.node(results, 'heat_dhw_demand_l')['sequences']
results_heat_ts['heat_space_demand'] = solph.views.node(results, 'heat_space_demand_l')['sequences']
results_heat_ts['heat_excess'] = solph.views.node(results, 'heat_excess_l')['sequences']

#%% Results: Overview plot

#Resample timestep to 1 day               
freq_sample='1H'
set_alpha=0.8

# Inilialize figure
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15,5) , sharey=False,sharex=False)
plt.subplots_adjust(wspace=0.25, hspace=0.05)

axes[0].plot(results_elec_ts['wind_onshore'].resample(freq_sample).sum(), alpha=set_alpha, color='royalblue', label='Wind onshore')
axes[0].plot(results_elec_ts['wind_offshore'].resample(freq_sample).sum(), alpha=set_alpha, color='blue', label='Wind offshore')
axes[0].plot(results_elec_ts['pv'].resample(freq_sample).sum(), alpha=set_alpha, color='gold', label='PV')
axes[0].plot(results_elec_ts['ror'].resample(freq_sample).sum(), alpha=set_alpha, color='black', label='RoR')
axes[0].plot(results_elec_ts['chp'].resample(freq_sample).sum(), alpha=set_alpha, color='green', label='CHP')

axes[0].plot(results_elec_ts['elec_demand'].resample(freq_sample).sum(), alpha=set_alpha, color='magenta', label='Electricty demand')
#axes[0].plot(results_elec_ts['elec_excess'].resample(freq_sample).sum(), alpha=set_alpha, color='cyan', label='Electricty excess')

axes[0].legend()
axes[0].set_ylabel('Energy electricty [MWh]')
axes[0].set_xlabel('Date')

axes[1].plot(results_heat_ts['chp'].resample(freq_sample).sum(), alpha=set_alpha, color='green', label='CHP')
axes[1].plot(results_heat_ts['hp'].resample(freq_sample).sum(), alpha=set_alpha, color='gold', label='Heat Pump')

axes[1].plot(results_heat_ts['heat_dhw_demand'].resample(freq_sample).sum(), alpha=set_alpha, color='red', label='DHW demand')
axes[1].plot(results_heat_ts['heat_space_demand'].resample(freq_sample).sum(), alpha=set_alpha, color='blue', label='Space heat demand')
#axes[1].plot(results_heat_ts['heat_excess'].resample(freq_sample).sum(), alpha=set_alpha, color='cyan', label='Heat excess')

axes[1].legend()
axes[1].set_ylabel('Energy Heat [MWh]')
axes[1].set_xlabel('Date')

plt.show()
fig.savefig('../results/analysis_ts_overview.png', dpi=300)
