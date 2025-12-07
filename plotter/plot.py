import json
from pathlib import Path

def nextOrNone(iterator):
    return next(iterator, None)

with open(Path(__file__).parent / "Journal.2025-12-06T173759.01.json") as f:
    journal = json.load(f)

loadout = nextOrNone(entry for entry in journal if entry.get("event") == "Loadout")
if loadout == None:
    exit()

fsd = nextOrNone(module for module in loadout.get("Modules") if module.get("Slot") == "FrameShiftDrive")
if fsd == None:
    exit()

fsd_booster = nextOrNone(module for module in loadout.get("Modules") if module.get("Item").startswith("int_guardianfsdbooster"))

fsd_engineering = fsd.get("Engineering")

fsd_superchargeMult = 6 if fsd.get("Item") == "int_hyperdrive_overcharge_size8_class5_overchargebooster_mkii" else 4

del loadout["Modules"]
print("Loadout:", json.dumps(loadout, indent=4))
print("FSD:", json.dumps(fsd, indent=4))
print("FSD Booster:", json.dumps(fsd_booster, indent=4))
print("FSD Engineering:", json.dumps(fsd_engineering, indent=4))

with open(Path(__file__).parent / "spansh.data.json") as f:
    dist = json.load(f)

std_ship_properties = dist.get("Ships").get(loadout.get("Ship")).get("properties")

std_fsd = nextOrNone(std_fsd for std_fsd in dist.get("Modules").get("standard").get("fsd")
     if std_fsd.get("symbol").lower() == fsd.get("Item"))

std_fsd_booster = nextOrNone(std_fsd_booster for std_fsd_booster in dist.get("Modules").get("internal").get("gfsb")
     if std_fsd_booster.get("symbol").lower() == fsd_booster.get("Item"))

std_fsd_engineering = dist.get("Modifications").get("blueprints").get(fsd_engineering.get("BlueprintName"))
std_fsd_engineering_exp_eff = dist.get("Modifications").get("modifierActions").get(fsd_engineering.get("ExperimentalEffect"))

print("Standard Ship Pops:", json.dumps(std_ship_properties, indent=4))
print("Standard FSD:", json.dumps(std_fsd, indent=4))
print("Standard FSD Booster:", json.dumps(std_fsd_booster, indent=4))
print("Standard FSD Engineering:", json.dumps(std_fsd_engineering, indent=4))
print("Standard FSD Exp Eff:", json.dumps(std_fsd_engineering_exp_eff, indent=4))

optimalMass = nextOrNone(mod for mod in fsd_engineering.get("Modifiers") if mod.get("Label") == "FSDOptimalMass").get("Value") or std_fsd.get("optmass")
maxFuelPerJump = nextOrNone(mod for mod in fsd_engineering.get("Modifiers") if mod.get("Label") == "MaxFuelPerJump") or std_fsd.get("maxfuel")
fuelMultiplier = std_fsd.get("fuelmul")
fuelPower = std_fsd.get("fuelpower")
tankSize = loadout.get("FuelCapacity").get("Main")
reservoirSize = loadout.get("FuelCapacity").get("Reserve")
baseMass = loadout.get("UnladenMass") + reservoirSize;
rangeBoost = std_fsd_booster.get("jumpboost")

print(f"params[\"optimal_mass\"]=\"{optimalMass}\"")
print(f"params[\"max_fuel_per_jump\"]=\"{maxFuelPerJump}\"")
print(f"params[\"fuel_multiplier\"]=\"{fuelMultiplier}\"")
print(f"params[\"fuel_power\"]=\"{fuelPower}\"")
print(f"params[\"tank_size\"]=\"{tankSize}\"")
print(f"params[\"base_mass\"]=\"{baseMass}\"")
print(f"params[\"range_boost\"]=\"{rangeBoost}\"")
print(f"params[\"internal_tank_size\"]=\"{reservoirSize}\"")
print(f"params[\"supercharge_multiplier\"]=\"{fsd_superchargeMult}\"")

# parseCoriolis() {
#   if (!this.configStruct.components) {
#     throw new Error('Could not decode json', {
#       cause: 'missing_config'
#     });
#   }
#   let blueprints = [];
#   for (const type in this.configStruct.components) {
#     if (type == 'standard') {
#       for (const slot in this.configStruct.components[type]) {
#         const component = this.configStruct.components[type][slot];
#         const blueprint = this.processCoriolisEngineeredComponent(component);
#         if (blueprint) {
#           blueprint.slot = this.standardMapping[slot] ?? slot;
#           blueprints.push(blueprint);
#         }
#       }
#     } else {
#       for (const component of this.configStruct.components[type]) {
#         if (component != null) {
#           const blueprint = this.processCoriolisEngineeredComponent(component);
#           if (blueprint) {
#             blueprint.slot = component.group;
#             blueprints.push(blueprint);
#           }
#         }
#       }
#     }
#   }
#   this.blueprints = blueprints;
#   const frameShiftDrive = this.configStruct.components.standard.frameShiftDrive;
#   const fsd = _dist.Modules.standard['fsd'].find(e => {
#     return e.class == frameShiftDrive.class && e.rating == frameShiftDrive.rating;
#   });
#   let optimalMass = fsd.optmass;
#   let maxFuelPerJump = fsd.maxfuel;
#   if (frameShiftDrive.modifications && frameShiftDrive.modifications.optmass) {
#     optimalMass *= 1 + frameShiftDrive.modifications.optmass / 10000;
#   }
#   if (frameShiftDrive.blueprint && frameShiftDrive.blueprint.special) {
#     const modifierAction = _dist.Modifications.modifierActions[frameShiftDrive.blueprint.special.edname];
#     if (modifierAction.optmass) {
#       optimalMass *= 1 + modifierAction.optmass;
#     }
#     if (modifierAction.maxfuel) {
#       maxFuelPerJump *= 1 + modifierAction.maxfuel;
#     }
#   }
#   this.optimalMass = optimalMass;
#   this.maxFuelPerJump = maxFuelPerJump;
#   this.fuelMultiplier = fsd.fuelmul;
#   this.fuelPower = fsd.fuelpower;
#   this.tankSize = this.configStruct.stats.fuelCapacity;
#   this.reservoirSize = this.calculateReservoirSize(this.configStruct.ship);
#   this.baseMass = this.configStruct.stats.unladenMass + this.reservoirSize;
#   this.configStruct.components.internal.forEach(module => {
#     if (module) {
#       if (module.group == 'Guardian Frame Shift Drive Booster') {
#         const gfsb = _dist.Modules.internal['gfsb'].find(e => {
#           return e.class == module.class && e.rating == module.rating;
#         });
#         if (gfsb) {
#           this.rangeBoost = gfsb.jumpboost;
#         }
#       }
#     }
#   });
# }
