"""Build reports/title-training.html: sample SKUs with the catalog crop, today's title and a draft
under Matthew's 2026-10-24 title rule, for him to say what he would have titled each one."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROW = "TPEAF-166L | 115/230 | 16.0/8.0 | 1-1/2 | 1.10 | 1.65 | UL‡ | 2\" x 2\" | 37 | F | Available Through Dealer"
# (mpn, page, group, today's title, draft title, draft fields)
S = [
 ("011057",198,"Whole good · pump","IntelliFlo® VS+SVRS Variable Speed Pump","IntelliFlo® VS+SVRS Variable Speed Pump",""),
 ("343001",218,"Whole good · Sta-Rite pump","SuperMax® VS Variable Speed Pump","SuperMax® VS Variable Speed Pump","brand: Sta-Rite"),
 ("460736",98,"Whole good · heater","MasterTemp® 400 Natural Gas High Performance Heater","MasterTemp® 400 Natural Gas High Performance Heater",""),
 ("160340",53,"Whole good · filter","Clean & Clear® Plus CCP320 Filter","Clean & Clear® Plus CCP320 Filter",""),
 ("602187",152,"Whole good · light","IntelliBrite® Architectural Series Color 120V 100 ft Cord Pool Light","IntelliBrite® Architectural Series Color 120V 100 ft Cord Pool Light",""),
 ("PKG 51",244,"Whole good · strainer","6 in Cast Iron Hair and Lint Strainer Trap with Basket for C, CC, and D Series Pumps","6 in Cast Iron Hair and Lint Strainer Trap with Basket","fits: C, CC and D Series pumps"),
 ("TPEAF-166L",0,"Website only · pump","Dyna-Jet Energy Efficient Single Speed 1-1/2 HP Spa and Water Features Pump","Dyna-Jet Energy Efficient Single Speed 1-1/2 HP Spa and Water Features Pump","brand: Sta-Rite; status: discontinued"),
 ("PA40",39,"Pleatco cartridge","Advanced Filter Cartridge 40 sq ft 7 in x 14-1/16 in","Advanced Filter Cartridge 40 sq ft 7 in x 14-1/16 in","fits: the filters in the Pleatco table"),
 ("179133",53,"Replacement cartridge pack","Clean & Clear® Plus Model 240 Pleatco Ultra Replacement Cartridge, Set of 4","Pleatco Ultra Replacement Cartridge, Set of 4","fits: Clean & Clear® Plus 240"),
 ("360230",307,"Part · one line (cleaner)","Racer® Rear Cover Kit","Cleaner Rear Cover Kit","product line: Racer®"),
 ("274416Z",502,"Part · one line (valve)","FullFloXF® Backwash Valve Center Diverter","Backwash Valve Center Diverter","product line: FullFloXF®"),
 ("519000",134,"Part · one line (skimmer)","QuikSkim Ultra Silt Sock","Skimmer Silt Sock","product line: QuikSkim Ultra"),
 ("170019",347,"Part · sized to its filter","FNS® Plus 24 sq ft Filter Tank Lid","Filter Tank Lid","product line: FNS® Plus; fits: 24 sq ft model"),
 ("357070S",468,"Part · model code","EQ Series® EQK1000 Pump Motor","Pump Motor","product line: EQ Series®; fits: EQK1000"),
 ("474241Z",400,"Part · model + build date","UltraTemp® Heat Pump ZP61 Scroll Compressor for Model 90 Only, FG Units Built Before 1/6/21","Heat Pump ZP61 Scroll Compressor","product line: UltraTemp®; fits: Model 90; fit note: FG units built before 1/6/21"),
 ("522978Z",326,"Part · automation","IntelliCenter® Battery for Indoor Control Panel and Outdoor Control Panel","Control Panel Battery","product line: IntelliCenter®; fits: Indoor and Outdoor Control Panel"),
 ("400010Z",432,"Part · shared, fit list","Pump Diffuser for IntelliFloXF®, WhisperFloXF®, IntelliProXF® and Max-E-ProXF®","Pump Diffuser","fits: IntelliFloXF®, WhisperFloXF®, IntelliProXF®, Max-E-ProXF®"),
 ("356210S",431,"Part · shared, fit list","Pump Ozone/Salt Resistant Mechanical Seal for Challenger®, SuperFlo®, SuperMax®, IntelliFlo3® and IntelliPro3® VSF","Pump Ozone/Salt Resistant Mechanical Seal","fits: Challenger®, SuperFlo®, SuperMax®, IntelliFlo3®, IntelliPro3® VSF"),
 ("350091Z",447,"Part · shared, no fit","Pump Lid","Pump Lid","fits: the pump pages it is listed on"),
 ("PP1010",243,"Part · kit for models","Parts-Paks™ Seal/Gasket Kit for PE, P2R 1/3 HP; PEA, P2RA 1/3, 1/2 HP; PRA 1/2 HP","Parts-Paks™ Seal/Gasket Kit","fits: PE, P2R 1/3 HP; PEA, P2RA 1/3, 1/2 HP; PRA 1/2 HP"),
 ("L1",291,"Part · competitor fit","9-7/8 in White Skimmer Lid with Thermometer for SwimQuip, Swimrite, Jacuzzi®, Hayward®","9-7/8 in White Skimmer Lid with Thermometer","fits: SwimQuip, Swimrite, Jacuzzi®, Hayward® skimmers"),
 ("79203200",417,"Part · application","Small Stainless Steel Niche Spa Plaster Ring for Gunite Niche","Small Stainless Steel Niche Spa Plaster Ring","application: gunite niche"),
 ("360337",304,"Part · cleaner models","Prowler® 910/Warrior® SL Power Supply","Cleaner Power Supply","fits: Prowler® 910, Warrior® SL"),
 ("R201536",426,"Part · numbered models","Replacement Brushes for No. 194 and No. 195","Replacement Brushes","fits: No. 194 and No. 195"),
 ("460741",104,"Accessory · for one model","NG to Propane Conversion Kit for MasterTemp® 250","NG to Propane Conversion Kit","fits: MasterTemp® 250"),
 ("25021-0021",59,"Accessory · model codes","S7M120/S7M400 Modular Media Conversion Kit","Modular Media Conversion Kit","fits: S7M120, S7M400"),
 ("356904Z",200,"Accessory · shared","Keypad Relocation Kit","Keypad Relocation Kit",""),
]
items = []
for mpn, page, group, now, draft, fields in S:
    it = {"id": re.sub(r"[^A-Za-z0-9-]", "_", mpn), "mpn": mpn, "group": group, "now": now, "draft": draft, "fields": fields}
    if page:
        it["crop"] = f"img/{mpn.replace(' ', '_')}_p{page}.png"; it["page"] = f"pages/page{page:03d}.jpg"; it["pno"] = page
    else:
        it["web"] = WEB_ROW; it["url"] = "https://www.pentair.com/en-us/pool-spa/products/pumps/dyna-jet-spa-water-features-pump.html"
    items.append(it)
review = (ROOT / "reports/pentair-review.html").read_text()
css = review[review.index("<style>"): review.index("</style>\n<style>")] + "</style>"
html = (ROOT / "scripts/training_template.html").read_text().replace("/*CSS*/", css).replace("/*ITEMS*/", json.dumps(items, ensure_ascii=False, indent=0))
(ROOT / "reports/title-training.html").write_text(html)
print(len(items), "items")
