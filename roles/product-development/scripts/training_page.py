"""Build reports/title-training.html: sample SKUs with the catalog crop, today's title and a draft
under Matthew's 2026-10-24 title rule, for him to say what he would have titled each one."""
import json, re, sqlite3
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
con = sqlite3.connect(ROOT / "data/catalog.db")
BRAND = dict(con.execute("SELECT mpn, brand FROM products"))
items = []
for mpn, page, group, now, draft, fields in S:
    it = {"id": re.sub(r"[^A-Za-z0-9-]", "_", mpn), "mpn": mpn, "group": group, "now": now, "draft": draft, "fields": fields, "brand": BRAND.get(mpn, "Pentair")}
    if page:
        it["crop"] = f"img/{mpn.replace(' ', '_')}_p{page}.png"; it["page"] = f"pages/page{page:03d}.jpg"; it["pno"] = page
    else:
        it["web"] = WEB_ROW; it["url"] = "https://www.pentair.com/en-us/pool-spa/products/pumps/dyna-jet-spa-water-features-pump.html"
    items.append(it)
review = (ROOT / "reports/pentair-review.html").read_text()
css = review[review.index("<style>"): review.index("</style>\n<style>")] + "</style>"
Q = [
 {"id": "discontinued", "title": "What should happen to discontinued SKUs?",
  "detail": "The database holds 1,003 discontinued SKUs: those the catalog marks discontinued, plus 37 from pentair.com with a Discontinued ribbon. None are in your export, but they still have titles. The same question applies to the 103 marked not for sale in the USA.",
  "choices": ["Delete them from the database", "Keep the number and status only, no title", "Keep as they are, just never export"]},
 {"id": "model-position", "title": "Where does a model name go in a part or accessory title?",
  "detail": "You wrote these three differently. 460741 prints “NG to Propane Conversion Kit - Model 250” and you put the model first. 25021-0021 prints “Modular Media Conversion Kit - S7M120/S7M400” and you kept it after a dash. 179133 prints “Model 240 Pleatco Ultra Replacement Cartridges (4/Pack)” and you dropped the model.",
  "examples": [["460741", "Model 250 NG to Propane Conversion Kit"], ["25021-0021", "Modular Media Conversion Kit - S7M120/S7M400"], ["179133", "Ultra Replacement Cartridge, Set of 4"]],
  "crops": ["img/460741_p104.png", "img/25021-0021_p59.png", "img/179133_p53.png"],
  "choices": ["Model in front of the noun", "Keep Pentair's “- Model” at the end", "Keep it for kits, drop it for cartridges", "Depends (note the rule)"]},
 {"id": "starite-accessories", "title": "Brand for parts and accessories of Sta-Rite lines",
  "detail": "My current rule makes every part and accessory Pentair, even on Sta-Rite pages (from your round 1 answer on IntelliProXF® parts). You made 25021-0021, a conversion kit for Sta-Rite's System:3® modular media filters, Sta-Rite.",
  "choices": ["Accessories follow the line's brand, parts stay Pentair", "Parts and accessories follow the line's brand", "25021-0021 is a special case (note why)"]},
 {"id": "r201536", "title": "R201536: 194R/195R or 196R?",
  "detail": "You wrote “196R Replacement Brushes”, but the row prints model 194R/195R (“For No. 194 and No. 195”). The next row, R201540, is the 196R one.",
  "crops": ["img/R201536_p426.png"],
  "choices": ["194R/195R Replacement Brushes", "196R was right"]},
 {"id": "eq-motor", "title": "How to read the EQ Series® motor chart, and what to call 357070S",
  "detail": "Each row is one pump model; the first column holds that pump's own part numbers. Reading across, the other columns are the replacement parts for that pump. 357070S sits in the “Motor No. (Item No. 1)” column on the EQK1000 row (10 HP, 3 phase), so it is the replacement motor for that pump. The column header is the only description Pentair prints. Every motor in the chart has the same column header. Swipe the chart sideways to see the Motor column.",
  "crops": ["img/357070S_chart_p468.png"],
  "choices": ["Motor", "10 HP 3 Phase Motor", "EQK1000 Motor", "Something else (note)"]},
 {"id": "pleatco", "title": "Pleatco cartridge titles",
  "detail": "Under “Advanced Filter Cartridge” with nothing added, 94 different Advanced cartridges share one title, and the 67 Ultra cartridges share another. Cartridges are usually chosen by size. Should the printed size stay?",
  "examples": [["PA40 today", "Advanced Filter Cartridge 40 sq ft 7 in x 14-1/16 in"], ["your answer", "Advanced Filter Cartridge"]],
  "choices": ["No size: Advanced Filter Cartridge", "Keep sq ft only", "Keep sq ft and dimensions"]},
 {"id": "marketing", "title": "Which words are marketing, not part of the name?",
  "detail": "You struck “High Performance” from the MasterTemp® heater. Tick every word below that should also go. The number is how many active whole-good titles use it.",
  "multi": True,
  "choices": ["High Performance (25)", "Variable Speed (26)", "Self-Priming (18)", "Commercial (99)", "DOE Compliant (4)", "Low Profile (6)", "Heavy Duty (3)"]},
 {"id": "series-specs", "title": "Specs on whole goods: every column that varies?",
  "detail": "For the IntelliBrite® light you added 28W although size, colour and voltage already told it apart. Should a whole-good title carry every spec column that varies in the series' ordering table (heater: gas type, BTU, ASME, HD; light: size, colour, voltage, watts, cord length)?",
  "choices": ["Yes, every column that varies", "Only the ones a buyer chooses by (note which)"]},
 {"id": "sqft", "title": "How should units be written?",
  "detail": "You wrote “24 Sq Ft”. Titles today use lower-case units: “24 sq ft”, “2 in”, “100 ft”.",
  "choices": ["Sq Ft (capitalized units)", "sq ft (lower case)"]},
 {"id": "disambiguate-scope", "title": "When two parts would get the same title",
  "detail": "You said to add something only when the same name appears in one parts list (24 vs 36 sq ft tank lid). Many parts share a name across different products (hundreds of “O-Ring”, “Lid”, “Impeller”). Is a duplicate title across different parts lists fine?",
  "choices": ["Yes, only disambiguate within one parts list", "No, disambiguate anywhere in the catalog"]},
]
html = (ROOT / "scripts/training_template.html").read_text().replace("/*CSS*/", css).replace("/*ITEMS*/", json.dumps(items, ensure_ascii=False, indent=0)).replace("/*QUESTIONS*/", json.dumps(Q, ensure_ascii=False, indent=0)).replace("/*HEADER*/", (ROOT / "scripts/training_header_r2.html").read_text()).replace("/*ITEMS_HEADING*/", "Round 1: your answers").replace("/*LABELS*/", json.dumps(["Today", "Draft", "Draft is right"]))
(ROOT / "reports/title-training.html").write_text(html)
print(len(items), "items")
