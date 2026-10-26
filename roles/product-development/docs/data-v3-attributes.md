# Attribute list (phase 3)

Each spec is `{attr, value, unit, raw}`. `value` is a number where the unit column says so, else
text. `raw` is the printed text it came from. Use these keys; anything else gets an `x_` prefix and
is reviewed. Ranges are written `{"min": a, "max": b}`. Several printed options are a list.

## Electrical / motor
| key | unit | meaning |
|---|---|---|
| hp | hp | rated horsepower |
| thp | hp | total horsepower (THP) |
| service_factor | — | SF |
| sfhp | hp | service-factor horsepower |
| voltage | V | text as printed ("208-230", "115/208-230") |
| phase | — | 1 or 3 |
| frequency | Hz | 50, 60 or "50/60" |
| amps | A | full-load amps (text if several) |
| watts | W | input power |
| wef | — | weighted energy factor |
| hhp | hp | hydraulic horsepower (HHP column) |
| min_speed | rpm | |
| max_speed | rpm | |
| conductors | — | wire count of a cable |
| speed_type | — | single, two, variable, variable speed and flow |
| motor_enclosure | — | TEFC, ODP |
| efficiency_class | — | Standard, High Efficiency, Premium |
| cord_length | ft | |
| low_voltage | — | 12V or 120V for lights |

## Hydraulics / plumbing
| key | unit | meaning |
|---|---|---|
| port_size | in | inlet x outlet as printed |
| pipe_size | in | |
| connection_type | — | slip, threaded, MPT, FPT, union, flange |
| thread_size | — | e.g. 3/8-16 |
| max_flow | gpm | |
| design_flow | gpm | |
| max_pressure | psi | |
| max_head | ft | |
| valve_positions | — | 2, 3, 6 position etc. |

## Filtration
| key | unit | meaning |
|---|---|---|
| filter_type | — | cartridge, D.E., sand, media |
| filter_area | sq ft | |
| tank_diameter | in | |
| sand_capacity | lb | |
| media_type | — | |
| cartridge_count | — | |
| cartridge_diameter | in | |
| cartridge_length | in | |
| top_hole | in | (text if a description) |
| bottom_hole | in | |
| pool_volume_max | gal | largest pool the item is rated for |
| turnover_hours | h | |
| mount | — | top, side |
| media_weight | oz/yd2 | cartridge fabric weight |

## Heating
| key | unit | meaning |
|---|---|---|
| btu_input | BTU/h | |
| btu_output | BTU/h | |
| fuel | — | natural gas, propane |
| asme | — | yes/no |
| cop | — | coefficient of performance (heat pumps) |
| heat_cool | — | heat only, heat/cool |
| min_air_temp | °F | |
| thermal_efficiency | % | |
| breaker_size | A | required breaker |
| heat_exchanger_material | — | cupro-nickel, copper, titanium |
| gas_line_size | in | |
| rating_condition | — | heat-pump BTU/COP rating condition, e.g. "80/80/80"; use with btu_output/cop as a list of {condition, btu_output, cop} in value |

## Lights / sanitizers / controls
| key | unit | meaning |
|---|---|---|
| lamp_type | — | LED, incandescent, halogen |
| color_mode | — | white, color, warm white |
| equivalent_watts | W | incandescent equivalent |
| lumens | lm | |
| chlorine_output | lb/day | |
| salt_ppm | ppm | |
| cell_size | — | IntelliChlor model etc. |
| circuits | — | number of circuits/relays |
| auxiliary_count | — | |
| personality_kit | — | |
| uv_lamp_count | — | |
| uv_watts | W | |

## Physical / general
| key | unit | meaning |
|---|---|---|
| color | — | as printed |
| material | — | |
| length | in | |
| width | in | |
| height | in | |
| diameter | in | |
| weight | lb | shipping or unit weight as printed |
| size | — | nominal size text that doesn't fit the above |
| pool_type | — | inground, aboveground, pool, spa, commercial (also an "Application" column) |
| surface | — | vinyl, gunite, fiberglass |
| pack_qty | — | items in the pack sold ("Set of 2", "2/pk") |
| case_pack | — | a "Pack #" / carton count column, not the sales unit |
| options | — | factory options that set this SKU apart from its siblings (relay board, touchscreen) |
| contents | — | what a kit includes (text) |
| certification | — | UL, NSF, ETL, CSA… as printed |
| program | — | dealer program mark shown for the item/family (TradeGrade, Energy Star) |
| warranty | — | as printed |
| replaces | — | older number this SKU replaces |
| replaced_by | — | newer number that replaces this SKU |
| upgrade | — | newer/better SKU the catalog offers as an upgrade (Pleatco ULTRA) |
| compatible_brands | — | competitor makes listed (Pleatco cross-refs) |
| cross_reference | — | competitor part numbers (Unicel, Filbur, Mfr #) |
| model_code | — | Pentair model code printed for the SKU |
| mfg_date_condition | — | "made after 6/17/19" etc. |
