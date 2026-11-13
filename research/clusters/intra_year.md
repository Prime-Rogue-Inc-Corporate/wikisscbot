# Intra-year address correlations

Archive fingerprint `615e22ede799`: 57,116 edits, 2009 to 2025. Each year is analysed on its own: only addresses with 5+ edits that year, only that year's edits.

- **pool**: 5+ handoffs within 60 min, or 3+ across 2+ pages. The addresses alternate inside one sitting.
- **same-exit**: 3+ shared rare pages (a rare page is one at most 3 addresses edited that year) without that many handoffs. Same traffic, but a sitting stays on one address.
- **linked**: exactly 2 shared rare pages.
- **one-page**: a single shared page with 3+ edits from each side. Weak; listed in the CSV only.

Gateway-level only. Nothing here says who is behind an address.

## How often the thresholds fire by chance

Pair-years reaching each threshold, by how the two addresses are related. Different blocks are the closest thing to a control.

| Relation | 2 shared rare pages | 3 or more |
|---|---|---|
| same /24 | 21 | 72 |
| same /16 | 19 | 12 |
| different block | 16 | 3 |

## Year summary

| Year | Edits | Addresses | Compared | Pool pairs | Same-exit pairs | Linked pairs | Groups | Cross-block groups |
|---|---|---|---|---|---|---|---|---|
| 2025 | 2,645 | 107 | 47 | 1 | 0 | 3 | 4 | 0 |
| 2024 | 1,249 | 129 | 50 | 1 | 0 | 3 | 2 | 1 |
| 2023 | 1,534 | 108 | 46 | 0 | 2 | 1 | 3 | 0 |
| 2022 | 2,157 | 107 | 55 | 0 | 3 | 0 | 2 | 0 |
| 2021 | 2,526 | 113 | 55 | 0 | 4 | 4 | 5 | 0 |
| 2020 | 1,518 | 100 | 43 | 0 | 0 | 1 | 1 | 0 |
| 2019 | 2,702 | 146 | 69 | 0 | 3 | 3 | 3 | 2 |
| 2018 | 3,704 | 160 | 64 | 0 | 8 | 5 | 4 | 2 |
| 2017 | 3,455 | 165 | 62 | 5 | 1 | 2 | 3 | 0 |
| 2016 | 2,617 | 163 | 64 | 0 | 6 | 1 | 2 | 0 |
| 2015 | 3,733 | 165 | 64 | 6 | 0 | 1 | 2 | 0 |
| 2014 | 3,151 | 173 | 67 | 6 | 1 | 4 | 4 | 0 |
| 2013 | 3,591 | 171 | 75 | 6 | 1 | 4 | 3 | 1 |
| 2012 | 4,150 | 202 | 80 | 7 | 0 | 5 | 3 | 1 |
| 2011 | 5,175 | 229 | 91 | 5 | 1 | 3 | 7 | 2 |
| 2010 | 6,333 | 253 | 97 | 7 | 2 | 3 | 6 | 2 |
| 2009 | 6,876 | 272 | 109 | 4 | 7 | 13 | 5 | 2 |

## Blocks whose addresses keep sharing traffic

Handoffs within the hour / shared rare pages, summed over the pairs inside each /24, per year. A fall in handoffs while shared pages hold up means the exit stopped alternating addresses inside a sitting.

| Block | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 131.137.245.x | 56/34 | 328/234 | 122/101 | 141/131 | 96/49 | 92/70 | 99/72 | 0/34 | 28/50 | 4/30 | 5/19 | 0/2 | 4/11 | 0/7 | 0/3 | · | · |
| 192.197.82.x | 5/18 | 14/16 | 47/30 | 28/25 | 0/2 | 0/4 | · | 0/2 | · | · | · | · | · | · | · | · | · |
| 207.35.15.x | · | · | · | · | · | · | · | · | · | 0/2 | · | 0/1 | 0/7 | · | 0/4 | 0/2 | · |

## Links across different blocks

Two addresses in unrelated blocks sharing rare pages inside one year. This is where a renumbering in progress, or one editor using two networks, shows up.

| Year | Addresses | Labels | Class | Shared rare | Closest edits (days) | Shared pages (top) |
|---|---|---|---|---|---|---|
| 2024 | 167.32.2.2 + 207.35.15.11 | House of Commons | linked | 2 | 62.88 | 2025 Canadian federal election; Marcus Powlowski |
| 2024 | 167.32.2.2 + 207.35.15.27 | House of Commons | linked | 2 | 63.02 | Marcus Powlowski; 2025 Canadian federal election |
| 2019 | 198.103.104.11 + 205.193.94.40 | SSC | linked | 2 | 71.06 | Chief William Commanda Bridge; Gord Miller (sportscaster) |
| 2019 | 199.212.18.130 + 205.211.133.128 | Environment Canada | linked | 2 | 36.09 | Indigenous land claims in Canada; Harvest |
| 2018 | 205.193.94.40 + 205.211.133.128 | SSC / Environment Canada | same-exit | 11 | 192.93 | British Columbia; Population of Canada by province and territory; Saskatchewan |
| 2018 | 192.197.82.153 + 207.35.15.27 | House of Commons | same-exit | 4 | 182.57 | Churence Rogers; Canadian House of Commons Liaison Committee; Matthew Dubé |
| 2018 | 198.103.167.20 + 205.193.94.40 | SSC | linked | 2 | 47.05 | North Preston; Elm Hill, New Brunswick |
| 2013 | 131.137.247.6 + 205.193.94.40 | National Defence / SSC | linked | 2 | 114.05 | List of law enforcement agencies in Canada; BlackBerry 10 |
| 2012 | 198.103.184.76 + 205.193.94.40 | SSC | linked | 2 | 4.83 | Employee assistance program; Philippe Falardeau [frwiki] |
| 2011 | 192.197.71.189 + 198.103.109.141 | SSC (AS2665) / SSC | linked | 2 | 54.06 | 2011 Vancouver Stanley Cup riot; Williams Lake, British Columbia |
| 2011 | 198.103.184.76 + 205.194.127.36 | SSC | linked | 2 | 48.27 | Biometrics; Richard Matheson |
| 2010 | 198.103.172.9 + 205.193.96.10 | SSC | same-exit | 3 | 194.05 | Wikipedia:Reference desk/Language; Wikipedia:Reference desk/Science; Wikipedia:Reference desk/Miscellaneous |
| 2010 | 199.212.17.130 + 205.211.133.129 | Environment Canada | linked | 2 | 160.09 | Centre météorologique canadien [frwiki]; Canada Gazette |
| 2009 | 131.137.245.200 + 198.103.184.76 | National Defence / SSC | linked | 2 | 13.65 | Bataille de Long Sault [frwiki]; Wiktionary:Feedback [enwiktionary] |
| 2009 | 131.137.245.206 + 198.103.167.20 | National Defence / SSC | linked | 2 | 46.96 | History of the Royal Canadian Navy; Royal Roads Military College |
| 2009 | 131.137.245.207 + 198.103.167.20 | National Defence / SSC | linked | 2 | 0.81 | History of the Royal Canadian Navy; Royal Roads Military College |
| 2009 | 131.137.245.207 + 198.103.184.76 | National Defence / SSC | linked | 2 | 123.34 | Wikipedia:Sandbox; Cadet Instructors Cadre; CHEK-DT |
| 2009 | 192.197.71.189 + 199.212.17.130 | SSC (AS2665) / Environment Canada | linked | 2 | 14.12 | Family Day; Franco-Ontariens [frwiki] |
| 2009 | 198.103.184.76 + 205.193.82.252 | SSC | linked | 2 | 6.87 | Fort Chambly [frwiki]; Rideau Centre |

## Pairs that recur across years

Pairs classed pool, same-exit or linked in three or more separate years.

| Addresses | Labels | Years | Of which pool | Handoffs |
|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 | National Defence | 14 (2009–2023) | 8 | 258 |
| 131.137.245.207 + 131.137.245.208 | National Defence | 12 (2010–2021) | 7 | 270 |
| 131.137.245.206 + 131.137.245.208 | National Defence | 10 (2010–2021) | 7 | 194 |
| 131.137.245.207 + 131.137.245.209 | National Defence | 9 (2012–2021) | 4 | 84 |
| 131.137.245.206 + 131.137.245.209 | National Defence | 8 (2012–2019) | 5 | 82 |
| 131.137.245.208 + 131.137.245.209 | National Defence | 7 (2012–2018) | 5 | 84 |
| 192.197.82.153 + 192.197.82.203 | House of Commons | 7 (2009–2016) | 4 | 82 |
| 192.197.82.155 + 192.197.82.205 | House of Commons | 4 (2009–2012) | 1 | 12 |
| 198.103.221.52 + 198.103.223.52 | SSC | 4 (2009–2018) | 2 | 11 |
| 198.103.152.52 + 198.103.223.52 | SSC | 4 (2009–2014) | 1 | 9 |
| 207.35.15.11 + 207.35.15.27 | House of Commons | 4 (2018–2024) | 0 | 0 |

## 2025

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 198.103.249.201 + 198.103.254.241 (SSC) | linked | 782 | 2 | 2 | Grand Sault-Vallée-des-Rivières-Saint-Quentin [frwiki]; Élections fédérales canadiennes de 2006 dans les territoires du Nord canadien [frwiki] |
| 205.193.239.44 + 205.193.239.76 (SSC) | pool | 311 | 36 | 13 | 30th Field Artillery Regiment, RCA; Commander of the Royal Canadian Air Force; Les Fusiliers de Sherbrooke [frwiki] |
| 198.103.184.84 + 198.103.184.85 (SSC) | linked | 33 | 0 | 2 | Abbotsford Canucks; Government of Canada Building (North York) |
| 167.32.2.2 + 167.32.2.3 (House of Commons) | linked | 23 | 0 | 2 | Eric Melillo; Vince Gasparro |

## 2024

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 205.193.239.44 + 205.193.239.76 (SSC) | pool | 229 | 10 | 12 | 1 Signal Regiment; HMCS Radisson; Dylan Everett |
| 167.32.2.2 + 207.35.15.11 + 207.35.15.27 (House of Commons) | linked · cross-block | 67 | 0 | 6 | 2025 Canadian federal election; Marcus Powlowski |

## 2023

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 (National Defence) | same-exit | 222 | 0 | 3 | Chris Daw; List of NHL franchise post-season droughts; Lord Strathcona's Horse (Royal Canadians) |
| 198.103.198.248 + 198.103.198.250 (SSC) | linked | 84 | 0 | 2 | Copenhagen Airport; Global Affairs Canada |
| 207.35.15.11 + 207.35.15.27 (House of Commons) | same-exit | 69 | 0 | 4 | 2025 Canadian federal election; Erin O'Toole; Sonia Sidhu |

## 2022

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 159.33.10.190 + 159.33.10.194 + 159.33.10.198 (CBC) | same-exit | 866 | 0 | 6 | Environment and Climate Change Canada; Patrick Brown (Canadian politician); 2022 Conservative Party of Canada leadership election |
| 131.137.245.206 + 131.137.245.207 (National Defence) | same-exit | 303 | 0 | 7 | Chris Daw; Medium Support Vehicle System; Sherbrooke Hussars |

## 2021

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 207.35.15.11 + 207.35.15.27 (House of Commons) | same-exit | 772 | 0 | 7 | List of shipwrecks in 1886; List of shipwrecks in 2021; List of shipwrecks in 1893 |
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | same-exit | 252 | 4 | 11 | 2021–22 Olympique de Marseille season; NATO Enhanced Forward Presence; 3rd Canadian Division |
| 159.33.10.190 + 159.33.10.198 (CBC) | linked | 44 | 0 | 2 | Mary Simon; Canadian Broadcasting Corporation |
| 198.103.152.35 + 198.103.223.35 (SSC) | same-exit | 26 | 0 | 3 | Céline Hervieux-Payette; Appendix:Translations of female given names in multiple languages [enwiktionary]; Talk:Ralph Nader 2000 presidential campaign |
| 198.103.152.36 + 198.103.223.36 (SSC) | linked | 21 | 1 | 2 | Caryl Chessman; List of radio stations in New Brunswick |

## 2020

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.207 + 131.137.245.208 (National Defence) | linked | 129 | 0 | 2 | American Indian Wars; Monarch of Jerusalem |

## 2019

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | same-exit | 509 | 5 | 19 | Judd Apatow; Ryan Rozicki; Canadian Army Command and Staff College |
| 198.103.104.11 + 205.193.94.40 (SSC) | linked · cross-block | 354 | 0 | 2 | Chief William Commanda Bridge; Gord Miller (sportscaster) |
| 199.212.18.130 + 205.211.133.128 (Environment Canada) | linked · cross-block | 107 | 0 | 2 | Indigenous land claims in Canada; Harvest |

## 2018

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | same-exit | 492 | 4 | 30 | Judd Apatow; 2e Division du Canada [frwiki]; Canadian Forces Military Police |
| 198.103.167.20 + 205.193.94.40 + 205.211.133.128 (Environment Canada, SSC) | same-exit · cross-block | 474 | 0 | 13 | North Preston; Elm Hill, New Brunswick; British Columbia |
| 192.197.82.153 + 207.35.15.11 + 207.35.15.27 (House of Commons) | same-exit · cross-block | 113 | 0 | 6 | Churence Rogers; Canadian House of Commons Liaison Committee; Matthew Dubé |
| 198.103.152.51 + 198.103.221.52 + 198.103.223.51 + 198.103.223.52 (SSC) | same-exit | 102 | 4 | 7 | 2018 Toronto municipal election; User talk:The Banner; Names of the British Isles |

## 2017

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | pool | 548 | 28 | 50 | Tracy Howe; John Charles Moore Grant, 9th Baron de Longueuil; Charles James Irwin Grant, 6th Baron de Longueuil |
| 198.103.152.52 + 198.103.221.51 (SSC) | linked | 68 | 0 | 2 | List of current senators of Canada; Template:Current Canada Senate vacant pending; Employment and Social Development Canada |
| 198.103.152.51 + 198.103.223.52 (SSC) | linked | 37 | 2 | 2 | Opinion polling for the April 2019 Israeli legislative election; Rockall |

## 2016

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | same-exit | 586 | 0 | 34 | Rational Youth; Ronald Charles Grant, 10th Baron de Longueuil; 3rd Canadian Division |
| 192.197.82.153 + 192.197.82.203 (House of Commons) | linked | 141 | 0 | 2 | Peter Kent; Stephen Fuhr |

## 2015

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | pool | 679 | 99 | 72 | HMCS Algonquin (DDG 283); Brioude [frwiki]; Sherbrooke Hussars |
| 198.103.152.51 + 198.103.223.51 (SSC) | linked | 30 | 0 | 2 | Responsibility for the Russo-Georgian War; Talk:Russo-Georgian War |

## 2014

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 (National Defence) | pool | 499 | 92 | 70 | St. John River campaign; HMCS St. John's; Commons:Village pump [commonswiki] |
| 198.103.104.11 + 198.103.184.76 (SSC) | linked | 361 | 0 | 2 | Law enforcement in Canada; Primary amoebic meningoencephalitis |
| 192.197.178.2 + 192.197.82.153 + 192.197.82.203 (House of Commons, Industry Canada) | same-exit | 324 | 1 | 8 | Dean Del Mastro; Karl Bélanger; Empire Field |
| 198.103.152.52 + 198.103.223.52 (SSC) | linked | 73 | 0 | 2 | Mitchell Kutney; Indicatifs régionaux 819, 873 et 468 [frwiki] |

## 2013

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 + 131.137.247.10 + 131.137.247.6 + 205.193.94.40 (National Defence, SSC) | pool · cross-block | 851 | 96 | 56 | HMCS St. John's; Commons:Village pump [commonswiki]; 41 Combat Engineer Regiment |
| 192.197.82.153 + 192.197.82.203 (House of Commons) | linked | 247 | 0 | 2 | Jamie Nicholls [frwiki]; Bal Gosal |
| 198.103.152.52 + 198.103.223.52 (SSC) | linked | 51 | 1 | 2 | All-India Muslim League; Baadshah (2013 film) |

## 2012

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 + 131.137.245.209 + 131.137.247.6 (National Defence) | pool | 724 | 141 | 133 | Royal Canadian Navy; Algonquin Regiment (Northern Pioneers); 4 Engineer Support Regiment |
| 198.103.184.76 + 205.193.165.2 + 205.193.94.40 (SSC) | linked · cross-block | 603 | 0 | 4 | Employee assistance program; Philippe Falardeau [frwiki]; Wikipedia:Tutorial (historical)/Formatting/sandbox |
| 192.197.82.153 + 192.197.82.155 + 192.197.82.203 + 192.197.82.205 (House of Commons) | pool | 346 | 28 | 25 | Sadia Groguhé [frwiki]; Hélène LeBlanc [frwiki]; Robert Sopuck |

## 2011

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 (National Defence) | pool | 671 | 122 | 101 | Norman Buchanan; Holy Trinity Catholic Secondary School (Courtice); Royal Canadian Infantry Corps |
| 198.103.184.76 + 205.194.127.36 (SSC) | linked · cross-block | 650 | 0 | 2 | Biometrics; Richard Matheson |
| 192.197.82.153 + 192.197.82.203 (House of Commons) | pool | 241 | 41 | 26 | Malcolm Allen (politician); Senators de Binghamton [frwiki]; Jonathan Genest-Jourdain [frwiki] |
| 192.197.71.189 + 198.103.109.141 (SSC, SSC (AS2665)) | linked · cross-block | 236 | 0 | 2 | 2011 Vancouver Stanley Cup riot; Williams Lake, British Columbia |
| 205.211.133.129 + 205.211.133.130 (Environment Canada) | same-exit | 178 | 0 | 3 | House Courcel; Kushiel's Legacy; House Shahrizai |
| 198.103.221.52 + 198.103.223.52 (SSC) | linked | 69 | 1 | 2 | Olivier Roy (ice hockey); Canucks de Vancouver [frwiki] |
| 192.197.82.155 + 192.197.82.205 (House of Commons) | pool | 68 | 6 | 4 | Dean Allison; Fort St. John, British Columbia; Jacques Gourde [frwiki] |

## 2010

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.206 + 131.137.245.207 + 131.137.245.208 (National Defence) | pool | 1,216 | 328 | 234 | 713e Régiment des communications [frwiki]; Cadet Instructors Cadre; List of Royal Military College of Canada memorials |
| 192.197.82.153 + 192.197.82.155 + 192.197.82.203 + 192.197.82.205 (House of Commons) | pool | 430 | 14 | 16 | Irene Mathyssen; Candice Bergen (politician); Kerguelen Islands |
| 198.103.152.52 + 198.103.221.52 + 198.103.223.52 (SSC) | pool | 284 | 19 | 17 | Gatineau [frwiki]; List of cinemas in Ottawa-Gatineau; United States anti-abortion movement |
| 198.103.172.9 + 205.193.96.10 (SSC) | same-exit · cross-block | 256 | 0 | 3 | Wikipedia:Reference desk/Language; Wikipedia:Reference desk/Science; Wikipedia:Reference desk/Miscellaneous |
| 199.212.17.130 + 205.211.133.129 (Environment Canada) | linked · cross-block | 121 | 0 | 2 | Centre météorologique canadien [frwiki]; Canada Gazette |
| 198.103.221.51 + 198.103.223.51 (SSC) | linked | 88 | 1 | 2 | Université Sainte-Anne [frwiki]; Critique de l'islam [frwiki] |

## 2009

| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |
|---|---|---|---|---|---|
| 131.137.245.197 + 131.137.245.199 + 131.137.245.200 + 131.137.245.206 + 131.137.245.207 + 198.103.152.51 + 198.103.152.52 + 198.103.167.20 + 198.103.184.76 + 198.103.221.51 + 198.103.221.52 + 198.103.223.51 + 198.103.223.52 + 205.193.82.252 (National Defence, SSC) | pool · cross-block | 2,621 | 67 | 87 | Essex, Ontario; Richmond Hill, Ontario; St. Theresa of Lisieux Catholic High School |
| 192.197.82.153 + 192.197.82.155 + 192.197.82.203 + 192.197.82.205 (House of Commons) | pool | 625 | 5 | 18 | 2009 Progressive Conservative Party of Ontario leadership election; Concours Eurovision de la chanson 2009 [frwiki]; John McKay (Ontario politician, born 1948) |
| 192.197.71.189 + 199.212.17.130 (Environment Canada, SSC (AS2665)) | linked · cross-block | 382 | 0 | 2 | Family Day; Franco-Ontariens [frwiki] |
| 199.212.150.16 + 199.212.150.17 (SSC network (AS2675)) | same-exit | 74 | 1 | 3 | Pacific Mall; Błażej Augustyn; Indigenous police in Canada |
| 142.206.2.12 + 142.206.2.15 (Statistics Canada) | linked | 50 | 2 | 2 | List of recipients of the Bronze Wolf Award; Capital Pride (Ottawa) |
