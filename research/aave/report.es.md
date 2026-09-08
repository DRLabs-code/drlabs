# Informe de investigación de Aave (AAVE)

**Investigación cripto de DRLabs**  
**Publicación / fecha de datos: 7 de septiembre de 2026 (Asia/Shanghai, UTC+8 / PT local del lector)**  
**Postura: neutra de investigación (no es asesoramiento de inversión)**

> **Síntesis en una línea:** Aave sigue siendo el líder de escala y de marca en lending on-chain. V3 concentra el grueso de la liquidez; V4 (Hub & Spoke) se lanzó en la mainnet de Ethereum en marzo de 2026 y aún está en una fase de caps conservadores. Los fundamentales dependen del ciclo de tipos, la cuota cross-chain y la alineación DAO–Labs — no de una historia de precio del token a corto plazo.

---

## 1. Panorama del proyecto

Aave es un protocolo de liquidez descentralizado y no custodial: los usuarios depositan activos en pools para ganar intereses, o piden prestado contra sobrecolateralización. Los smart contracts emparejan oferta y demanda y liquidan posiciones de riesgo sin un custodio. El nombre proviene del finlandés para “fantasma”, un guiño a una infraestructura transparente e invisible.

**Problema que resuelve:** El crédito tradicional depende de intermediarios y de underwriting. Los mercados on-chain han enfrentado durante mucho tiempo liquidez fragmentada y parámetros de colateral/riesgo difíciles de extender de forma modular. Aave sustituyó el emparejamiento peer-to-peer temprano por un modelo de pool y siguió iterando en aislamiento de riesgo, despliegue multi-cadena y una stablecoin nativa (GHO).

**Posicionamiento:** Infraestructura central de “money market” DeFi. En DefiLlama, la familia Aave (sobre todo V3) ha liderado durante mucho tiempo el TVL de lending. Los materiales oficiales reivindican originaciones acumuladas por encima de la marca de $1 trillion y más de la mitad del lending descentralizado (definición del blog oficial — contrastar con la cuota de TVL de terceros).

**Historia breve:** En 2017 Stani Kulechov (hoy CEO de Aave Labs) lanzó lending peer-to-peer como ETHLend; el proyecto pasó luego a pools de liquidez, se rebrandó a Aave y salió en la mainnet de Ethereum hacia principios de 2020. En octubre de 2020 LEND migró 100:1 al token de gobernanza AAVE. Luego llegaron V2, V3 multi-cadena, GHO, Safety Module→Umbrella y el lanzamiento de V4 en mainnet en 2026.

---

## 2. Producto y mecánica

### 2.1 Mercados de lending y el modelo de tipos

- **Supply / borrow:** Los suppliers reciben recibos que generan intereses. El borrowing exige sobrecolateralización. Los tipos siguen una curva de utilización (más plana por debajo de la utilización óptima, empinada por encima). Los tipos de supply son el interés del borrower menos las comisiones del protocolo, compartidos entre suppliers.
- **Arquitectura V3:** La liquidez se aísla por mercado (p. ej. Ethereum Core / Prime). Los pools en la misma cadena no reutilizan fondos entre mercados — mejor aislamiento de riesgo, pero los mercados nuevos deben bootstrapear liquidez por su cuenta.
- **eMode (Efficiency Mode):** Eleva la capacidad de borrowing para activos altamente correlacionados (pares estables, ETH/LST) y mejora la eficiencia de capital.
- **aToken:** Los recibos de supply de V3 son en su mayoría aTokens rebasing; los saldos crecen con el interés y pueden componerse en otros puntos de DeFi.

### 2.2 Liquidaciones

Las posiciones con Health Factor por debajo de 1 pueden liquidarse. Los liquidadores pagan parte de la deuda y reciben colateral más un bono. El protocolo depende de precios de oráculos; la congestión de liquidaciones, la deuda incobrable y el lag de oráculos son los riesgos de cola centrales en estrés.

### 2.3 Aave V4 (estado según fuentes oficiales)

**Lanzamiento:** Blog oficial con fecha **30 March 2026** para V4 en la mainnet de Ethereum.

**Cambio central — Hub & Spoke:**

| Componente | Rol |
|------|------|
| Liquidity Hub | Hub on-chain unificado de liquidez y contabilidad; fija límites de crédito/débito para los Spokes |
| Spoke | Entrada de cara al usuario; puede fijar su propio colateral, parámetros de riesgo y reglas de liquidación |
| Risk Premium | Prima extra de borrow sobre el tipo de utilización, según la calidad del colateral |
| Liquidation engine | El Health Factor objetivo sustituye un close factor fijo; bonos variables; reglas de dust |

Nota oficial: V4 se lanzó con varios Liquidity Hubs (narrativas Core / Prime / Plus y similares). **Los caps de supply y borrow fueron deliberadamente conservadores**, para que el DAO los eleve tras observar producción. En el lado de UI se lanzó **Aave Pro** para V4. En seguridad, los materiales oficiales citan unos 345 días acumulados de auditoría, varias firmas y un concurso público de Sherlock (véase el repo de auditorías).

**Contabilidad:** Los escritos comunitarios y técnicos describen en general que V4 se mueve hacia contabilidad de shares ERC-4626 (frente a aTokens rebasing de V3). El UX de producto sigue la documentación oficial y la UI.

**Relación con V3:** Los materiales oficiales y de gobernanza son explícitos en que **V3 seguirá funcionando mientras se necesite**. V4 es la siguiente arquitectura de liquidez unificada; la migración y el desplazamiento de cuota son un proceso de medio plazo.

### 2.4 Despliegue multi-cadena

Aave está live en Ethereum más múltiples L2s/sidechains y L1s más nuevas (mix de cadenas de DefiLlama más abajo). La ruta oficial de V4: probarlo en la mainnet de Ethereum, luego dejar que el DAO añada Spokes, eleve caps y empuje más redes.

### 2.5 GHO y productos de ahorro

**GHO** es la stablecoin nativa de Aave, sobrecolateralizada y pegada al USD: los usuarios mintean (borrow) GHO contra colateral y lo queman al devolver. El interés de borrow fluye en su mayor parte a la tesorería del DAO. Los datos de stablecoins de DefiLlama alrededor del **7 September 2026** sitúan el mcap circulante de GHO en unos **$698 million**, precio de unos **$0.999**, cerca de $1.

![Oferta circulante de GHO](charts/05_gho_circulating.png)

**Lectura:** GHO tiene un flotante cercano a $700 million y un peg estable hasta ahora. Frente a USDT/USDC y las stables más nuevas que generan yield sigue siendo de tamaño medio. El crecimiento depende de la demanda de borrow, la competitividad de sGHO y la liquidez cross-chain.

**sGHO / Aave Savings Rate (ASR):** La gobernanza está moviendo el lado de ahorro a un vault ERC-4626 (sGHO). En una propuesta de GHO Stewards de agosto de 2026, el ASR se discutió en unos **4.50%** (con algunos tipos de borrow de GHO por cadena elevados en paralelo) para igualar tipos de ahorro competidores y la retención. La ejecución sigue los parámetros on-chain y la UI.

**GSM y otras herramientas de estabilidad:** Se usan para defensa del peg y buffers de liquidez. Los depegs, la basis cross-chain y el desajuste de tipos siguen siendo riesgos a nivel de producto.

---

## 3. Economía del token (AAVE)

| Partida | Datos (7 September 2026) | Fuente |
|------|----------------------|------|
| Oferta máxima / total | 16,000,000 AAVE | Parámetros públicos del token / Etherscan |
| Circulante (implícito) | ~15.54M (~97.1%) | mcap DefiLlama ÷ spot |
| Precio | ~$134.55 | DefiLlama coins API |
| Mcap circulante | ~$2.09B | mcap de protocolo DefiLlama |
| FDV (a 16M) | ~$2.15B | Spot × oferta máxima |
| Variación 30 días | ~+49% (impresión borrador de CoinGecko; no rechequeada tras throttle de API) | CoinGecko (cita histórica) |
| Variación 1 año | ~−55% (igual) | CoinGecko (cita histórica) |

![Capitalización de mercado y FDV de AAVE](charts/04_aave_mcap_fdv.png)

**Lectura:** La circulación está cerca de fully diluted; la brecha entre mcap y FDV es pequeña (~3%). La historia habitual de “unlock overhang” es débil. La elasticidad del token viene más de la prima de gobernanza, los ingresos esperados del DAO y el apetito de riesgo que de un squeeze de oferta.

**Usos:**

1. **Gobernanza:** El Aave DAO (foro → TEMP CHECK / ARFC → AIP) vota parámetros, listings, comisiones y gasto de tesorería.  
2. **Seguridad e incentivos:** El Safety Module histórico usaba **stkAAVE** y activos similares para riesgo de slashing más incentivos. Se ha actualizado a **Umbrella** (aTokens / activos relacionados que cubren deuda incobrable, con slashing automatizado). stkAAVE puede conservar cierta utilidad e incentivos en la transición, pero el centro de ayuda oficial dice que ya no es el activo preferido de cobertura de deuda incobrable.  
3. **Narrativa de captura de valor:** El **marco “Aave Will Win”** aprobado hacia abril de 2026 dirige los ingresos de productos de marca Aave a la tesorería del DAO, reforzando “tener AAVE ≈ derechos económicos en el protocolo y la marca”. Las vías para que los ingresos de la capa de apps (Aave Pro / App y similares) entren en la tesorería siguen la ejecución de gobernanza.

**Unlocks:** Oferta fija de 16 million, casi toda circulante; el resto principalmente en contratos de reserva/incentivos del ecosistema. **No se encontró un cliff unlock material.** La presión de oferta a corto plazo viene más de emisiones de incentivos y operaciones de tesorería que de vesting clásico.

---

## 4. Mercado y fundamentales

> Nota: los proveedores de datos definen “TVL” de forma distinta. El TVL de protocolo de DefiLlama suele acercarse a “neto bloqueado” (supply menos borrows y ajustes similares). Aavescan también muestra supply, borrows y TVL neto. Los gráficos aquí usan la **API auditable de DefiLlama**. Aavescan se renderiza en front-end y no pudo scrapearse de forma estable en esta ronda, así que no se usa para gráficos independientes.

### 4.1 Escala

| Métrica | Valor | Fecha / fuente |
|------|------|-----------|
| TVL del protocolo Aave (padre DefiLlama) | ~**$18.40B** | 2026-09-07, [DefiLlama API](https://defillama.com/protocol/aave) |
| Supply (est.) / borrows / TVL neto | ~**$31.2B / $12.85B / $18.4B** | DefiLlama: supply ≈ TVL neto + Borrowed |
| TVL de Aave V3 | ~**$17.64B** | Protocolos DefiLlama |
| TVL de Aave V4 | ~**$0.384B** | Igual (caps conservadores tras el lanzamiento; aún pequeño) |
| TVL de Aave V2 | ~**$0.112B** | Igual (legado) |

![TVL de Aave por versión](charts/01_aave_tvl_versions.png)

**Lectura:** De ~$18.4B de TVL neto del padre, V3 es unos 96%. V4 es unos $384M — caps conservadores más migración temprana. La historia de arquitectura está live; la liquidez aún no ha cambiado.

![Supply, borrows y TVL neto](charts/02_aave_supply_borrow_net.png)

**Lectura:** Borrows ~$12.9B y TVL neto ~$18.4B sitúan la utilización en un rango que produce comisiones. El lado de supply (neto + borrowed) ~$31.2B muestra la escala de balance del protocolo.

![Tendencia de TVL neto de Aave](charts/07_aave_tvl_trend.png)

**Lectura:** El TVL neto del último año rodó desde un pico de finales de 2025, bajó a escalones a mediados de 2026 y luego se recuperó en agosto–septiembre hasta unos $18.4B — **sigue siendo el líder de escala, claramente cíclico**, muy ligado a los activos de riesgo y a los flujos de stablecoins.

### 4.2 Ingresos y comisiones (DefiLlama Fees)

| Métrica | Aprox. | Fuente |
|------|------|------|
| Comisiones del protocolo, 30d | ~**$32.8M** | DefiLlama fees/aave, 2026-09-07 |
| Ingresos del protocolo, 30d | ~**$4.57M** | Igual (dailyRevenue) |
| Comisiones / ingresos, all-time | ~**$2.28B / $309M** | Igual |

![Comisiones a 30 días vs ingresos del protocolo](charts/03_aave_fees_vs_revenue_30d.png)

**Lectura:** Últimos 30 días ~$32.8M de comisiones y ~$4.57M de ingresos del protocolo, una tasa de captura de unos **13.9%** (el resto va sobre todo a suppliers). La escala de comisiones lidera el lending, pero la captura en la capa del token aún depende del reserve factor, el interés de GHO y la ejecución de “Aave Will Win” — no del titular de comisiones por sí solo.

**Nota:** El último día de una serie de ingresos diarios puede estar incompleto; preferir agregados de 7/30 días.

### 4.3 Cuota competitiva (DefiLlama, 7 September 2026)

| Protocolo | TVL aprox. |
|------|----------|
| Aave V3 | $17.6B |
| Morpho Blue | $9.8B |
| SparkLend | $4.5B |
| Compound V3 | $1.4B |
| Fluid Lending | $0.75B |
| Aave V4 | $0.38B |
| Euler V2 | $0.35B |

![TVL de competidores de lending](charts/06_lending_competitors_tvl.png)

**Lectura:** Aave V3 sigue liderando con un margen amplio. Morpho Blue en ~$9.8B es el seguidor más cercano, compitiendo en yield y eficiencia de capital. La cuota de Compound V3 se ha encogido. Spark se sitúa en la órbita de Sky y es a la vez competidor y complemento de la liquidez de Aave.

### 4.4 Mix de cadenas (DefiLlama currentChainTvls, excluding borrowed/staking/pool2)

Unos **84.8%** del TVL neto está en **Ethereum** (~$15.6B); luego Base, Plasma, Arbitrum, Monad, Avalanche, BSC, Polygon y otros. Borrows totales ~**$12.85B**. La expansión multi-cadena está en marcha, pero el riesgo y los ingresos siguen muy concentrados en Ethereum.

---

## 5. Gobernanza, equipo / trasfondo de la fundación

- **Aave Labs:** Entidad de producto e I+D liderada por el fundador **Stani Kulechov**, que cubre iteración del protocolo, front ends y trabajo de marca.  
- **Aave DAO:** Los tenedores de AAVE y los delegates gestionan parámetros, listings, tesorería y upgrades mayores vía [governance.aave.com](https://governance.aave.com) y gobernanza on-chain.  
- **Stack de proveedores de servicios:** Históricamente BGD Labs, proveedores de riesgo, ACI y otros contribuyeron al desarrollo y a las operaciones de gobernanza. Hacia 2026, la fricción pública sobre financiación y poder (algunos proveedores redujeron o dejaron de contribuir) es un ítem de seguimiento de gobernanza.  
- **Marco “Aave Will Win” (~aprobado April 2026):** Dirige los ingresos de productos de marca Aave al DAO; da a Labs un presupuesto de unos un año; se compromete a una propuesta posterior para que marca/IP residan en un vehículo de protección comunitaria (tipo fundación). CoinDesk y otros lo llamaron un hito que cierra la pelea de “quién se queda los ingresos”, al tiempo que plantean preguntas de centralización y accountability.  
- **Riesgo y operaciones de parámetros:** Roles como Risk Steward, GHO Stewards y similares pueden ajustar tipos dentro de un mandato — respuesta más rápida, más riesgo delegado.

La información pública no muestra una única fundación tradicional que sustituya por completo a Labs. La estructura legal final de cualquier vehículo de fundación/IP sigue AIPs posteriores. **Esta nota señala: el marco está aprobado, los detalles aún hay que seguirlos.**

---

## 6. Competencia y foso

**Foso (relativamente sólido):**

1. **Efectos de red de liquidez y confianza de marca:** Los pools profundos recortan el slippage de tamaño grande y el shock de tipos; las instituciones y tesorerías prefieren venues testeados en batalla.  
2. **Multi-cadena y matriz de producto:** V3 multi-mercado + GHO + Umbrella + Horizon (lending RWA, listado por separado en DefiLlama) + Spokes modulares de V4.  
3. **Experiencia de liquidación y riesgo:** Múltiples ciclos de estrés cripto; los materiales oficiales subrayan el historial de pressure-test en producción.  
4. **Gobernanza y amplitud de integración:** Coste de cableado por defecto para wallets, aggregators y productos estructurados.

**Desafíos:**

- **Morpho y pares:** Mayor eficiencia de capital y yield curado pueden sifonar depósitos marginales.  
- **Fricción de migración de V4:** Split de doble versión; los caps conservadores mantienen pequeña la cuota de V4 a corto plazo.  
- **Tensión DAO–Labs:** Afecta la previsibilidad de los contribuidores externos y la cadencia de upgrades.  
- **Guerras de stablecoins:** sUSDS, Ethena y otros productos de ahorro comprimen el crecimiento de GHO/sGHO.

---

## 7. Riesgos (solo exposiciones, sin detalle de exploits)

| Categoría | Exposición |
|------|--------|
| Smart contracts | Complejidad de V3/V4/Umbrella/GHO; la superficie de ataque se ensancha en el lanzamiento de nueva arquitectura; depende de auditorías continuas y métodos formales |
| Oráculos | El lag o la manipulación pueden causar liquidaciones malas o deuda incobrable; multi-cadena multiplica la dependencia de oráculos |
| Gobernanza | Propuestas maliciosas o precipitadas, errores de parámetros, concentración de delegates; bordes de permiso de Steward |
| Regulación | Lending y stables enfrentan incertidumbre de valores/stablecoins por jurisdicción; domicilio de la entidad de front end y Labs |
| GHO / stables | Depeg, liquidez cross-chain delgada, tipo de ahorro insostenible, agotamiento del GSM |
| Liquidez y cisnes negros | Liquidaciones en cascada, depegs de stables, descuentos de LST, riesgo de bridge, contagio de protocolos relacionados |
| Operaciones y política | Salidas de proveedores, disputas de marca/IP, incentivos demasiado delgados vs cobertura objetivo |

Umbrella alinea los activos slasheados con los activos de deuda incobrable potencial y añade un buffer de déficit. El lenguaje del centro de ayuda oficial dice que el Safety Module histórico estuvo largo tiempo sin un slash real — **eso no es una promesa de cero en el futuro**.

---

## 8. Catalizadores y métricas de seguimiento

**Catalizadores potenciales:**

- Subidas de caps de V4, nuevos Spokes (institución/RWA/tipo eMode) y más deploys de cadena  
- Flotante de GHO y depósitos de sGHO rompiendo al alza; efectividad de la política de ASR y de tipos de borrow  
- Ejecución del enrutado de ingresos del DAO y cualquier propuesta de “buyback / incentivo / dividendo” (evaluar por separado si aparecen)  
- Aterrizaje de los detalles de la fundación de marca, enfriando la narrativa de split de gobernanza  
- Un ciclo de tipos al alza que eleve comisiones e ingresos

**Métricas semanales sugeridas:**

1. DefiLlama: TVL del padre Aave / V3 / V4 y mix de cadenas  
2. Comisiones e ingresos (7d/30d) más utilización  
3. Mcap circulante de GHO, desviación del peg, TVL de sGHO, ASR  
4. Stake de Umbrella por activo versus cobertura objetivo  
5. Cuota relativa de TVL de Morpho / Spark / Compound  
6. Foro de gobernanza: parámetros de V4, Risk Steward, presupuestos de proveedores y propuestas de fundación  
7. Oferta circulante de AAVE y tenencias de tesorería (on-chain)

---

## 9. Conclusión y lista de seguimiento

**Conclusión:** En 2026 Aave sigue siendo el “protocolo sistémico” del lending DeFi: TVL neto en torno a $18B, escala de comisiones a la cabeza, V4 live pero aún sin cargar la liquidez central. En el token, la oferta está casi plenamente circulante; el valor está más ligado a los derechos de ingresos del DAO y a una prima de gobernanza. El marco de gobernanza de 2026 reforzó “ingresos al DAO”, pero la calidad de ejecución y la estabilidad del stack de contribuidores aún necesitan prueba. Para lectores orientados a la investigación, Aave encaja como **tenencia de referencia del sector de lending y seguimiento de infraestructura**. Las decisiones de trading necesitan una visión aparte de tipos macro, apetito de riesgo y fugas competitivas.

**Lista de seguimiento:**

- [ ] Si el TVL neto de V4 sigue rompiendo al alza (pendiente de migración versus V3)  
- [ ] Si los ingresos del protocolo a 30 días se recuperan con la utilización (versus picos de 2025)  
- [ ] Si GHO se mantiene cerca de $1 con entradas netas en el lado de ahorro  
- [ ] Si la cobertura de Umbrella alcanza los objetivos de gobernanza sin déficits extraños  
- [ ] Si las relaciones DAO–Labs y los contribuidores externos se reestabilizan  
- [ ] Si Morpho y otros siguen comiéndose el crecimiento marginal

---

## 10. Resumen objetivo y puntuación de compra

**Fecha de corte: 7 September 2026 (Asia/Shanghai, UTC+8)**

Esta sección es una puntuación estructurada bajo el marco interno de investigación de DRLabs, usada para comparar el atractivo relativo dentro del mismo sector. **No es una recomendación de compra, mantenimiento o venta para ningún lector** (véase el descargo al final).

### 10.1 Escala de puntuación (1–10)

| Puntuación | Significado (definición de investigación) |
|------|------------------|
| 1 | Fundamentales gravemente deteriorados o un fallo estructural difícil de aceptar; el marco se inclina a evitar |
| 2–3 | La incertidumbre mayor domina; los negativos superan con claridad el foso y la lógica de flujo de caja |
| 4–5 | Seguible pero de atractivo limitado; solo para apetito de riesgo muy alto o tamaño event-driven |
| 6 | Fundamentales aceptables con puntos de debate claros; discutir como seguimiento o satélite pequeño |
| 7 | La posición sectorial y los fundamentales se inclinan a positivo, aún constreñidos por competencia, gobernanza o valoración |
| 8 | Atractivo relativo más fuerte; varios factores puntúan alto; el resto es sobre todo ejecución y macro |
| 9 | La cadena de evidencia es muy fuerte, los negativos limitados; el marco se inclina a discutir sobreponderación de alta confianza |
| 10 | Caso “must own” extremadamente escaso; foso, crecimiento, captura y valoración casi sin un agujero mayor |

### 10.2 Factores y pesos

| Factor | Peso | Puntuación (1–10) | Base breve (2026-09-07) |
|------|------|-------------|------------------------|
| Fundamentales / foso | 25% | **8.0** | TVL neto ~$18.4B, marca e integraciones a la cabeza; experiencia profunda de liquidación y multi-cadena |
| Crecimiento y cuota | 20% | **6.5** | Sigue #1, pero Morpho Blue ~$9.8B está cerca; la cuota de V4 aún es pequeña |
| Captura de valor del token | 20% | **6.5** | “Aave Will Win” refuerza los ingresos del DAO; ingresos/comisiones 30d ~13.9%; el ritmo de ejecución no está probado |
| Riesgo (más alto = más contenido) | 20% | **5.5** | Complejidad de contratos y cross-chain, fricción de gobernanza, regulación y competencia de stablecoins son constreñimientos reales |
| Valoración y timing | 15% | **6.5** | Casi plenamente circulante, brecha mcap/FDV pequeña; gran drawdown a 1y y luego un rebote — hay margen de timing, no prueba de infravaloración extrema |

**Puntuación ponderada:**  
`0.25×8.0 + 0.20×6.5 + 0.20×6.5 + 0.20×5.5 + 0.15×6.5 = 6.675` → **puntuación de compra final: 6.7 / 10**

### 10.3 Por qué 6.7, no más alto ni más bajo

- **No 8+:** Morpho y pares pueden disputar la cuota marginal; la migración de liquidez de V4 es lenta; las relaciones DAO–Labs y de proveedores siguen ruidosas; la captura de ingresos del protocolo versus comisiones es limitada, y la ejecución de gobernanza es path-dependent.  
- **No por debajo de 5:** La escala, el volumen de comisiones y la confianza de marca siguen liderando a Compound y otros pares legacy; la oferta es limpia; GHO más ingresos-al-DAO es una opción de medio plazo; el TVL se ha reparado desde el mínimo de mitad de año.  
- **Discutible:** Los lectores que sobreponderan “token = flujo de caja” y quieren mayor certeza de captura pueden imprimir 5–6; los que sobreponderan escasez de infra sistémica y adopción institucional pueden imprimir 7–7.5. Esta nota toma el centro ponderado **6.7** — “un seguimiento de referencia sectorial con sesgo positivo, no una sobreponderación incondicional”.

---

## 11. Descargo de responsabilidad

Este informe lo compila DRLabs a partir de información pública y es **solo para información general y discusión de investigación**. No es, y no debe leerse como, asesoramiento de inversión, una recomendación, una oferta, una captación ni ninguna forma de compromiso respecto a valores, activos digitales u otros productos financieros.

Los criptoactivos y los protocolos DeFi son altamente volátiles e inciertos. Los precios y los parámetros del protocolo pueden moverse con violencia en poco tiempo. Los inversores pueden perder parte o la totalidad de su principal. Los lectores deben juzgar de forma independiente según sus finanzas, tolerancia al riesgo y objetivos, y consultar a asesores cualificados si es necesario. **Cualquier decisión basada en este informe, y sus consecuencias, es del propio lector.**

La “puntuación de compra” y las puntuaciones de factores son **cuantificaciones subjetivas** bajo un marco declarado y las restricciones de datos públicos, usadas para comparación interna y discusión. **No son una recomendación de compra o venta sobre ningún activo digital** y no garantizan el desempeño futuro del mercado.

Los datos, gráficos y fuentes de terceros citados (incluidos, entre otros, DefiLlama, documentación oficial y foros de gobernanza) pueden diferir en definición, estar retrasados, incompletos o ser erróneos. DRLabs y el autor no hacen garantía expresa ni implícita de exactitud, integridad, puntualidad o idoneidad, y no son responsables de ninguna pérdida directa o indirecta por usar o confiar en este informe. Los mercados y el estado del protocolo cambian rápido; rechequee las fuentes originales y el estado on-chain antes de citar.

---

## 12. Fuentes

1. [Aave V4 Overview (documentación oficial)](https://aave.com/docs/aave-v4)  
2. [Understanding Aave V4’s Architecture (blog oficial)](https://aave.com/blog/understanding-aave-v4s-architecture)  
3. [Aave V4 is Live on Ethereum (blog oficial, 2026-03-30)](https://aave.com/blog/aave-v4-live-ethereum)  
4. [Sitio web de Aave](https://aave.com)  
5. [DefiLlama — Aave](https://defillama.com/protocol/aave)  
6. [DefiLlama — Aave V3](https://defillama.com/protocol/aave-v3)  
7. [DefiLlama — stablecoin GHO](https://defillama.com/stablecoin/gho)  
8. [Aavescan Protocol Totals](https://aavescan.com/protocol/totals) (no usado para gráficos en esta ronda)  
9. [CoinGecko — Aave](https://www.coingecko.com/en/coins/aave) (algunas cifras de retorno son citas históricas; API throttled el día del gráfico)  
10. [Ayuda de Umbrella](https://aave.com/help/umbrella/umbrella)  
11. [BGD: Safety Module — Umbrella (foro de gobernanza)](https://governance.aave.com/t/bgd-aave-safety-module-umbrella/18366)  
12. [Actualización de tipos y ASR de GHO Stewards de agosto de 2026](https://governance.aave.com/t/gho-stewards-august-2026-gho-borrow-rate-and-aave-savings-rate-update/25534)  
13. [Propuesta de herramienta de migración stkGHO → sGHO](https://governance.aave.com/t/direct-to-aip-stkgho-sgho-migration-tool/25250)  
14. [[ARFC] Aave Will Win Framework](https://governance.aave.com/t/arfc-aave-will-win-framework/24352)  
15. [CoinDesk: votación Aave Will Win](https://www.coindesk.com/tech/2026/04/13/aave-passes-landmark-vote-ending-months-long-fight-over-who-controls-protocol-revenue)  
16. [DL News: fricción DAO vs Labs](https://www.dlnews.com/articles/defi/aave-dao-members-accuse-stani-kulechov-of-power-grab/)  
17. [Overview de Aave V4 en GitHub](https://github.com/aave/aave-v4/blob/main/docs/overview.md)  
18. [Wikipedia — Aave (trasfondo)](https://en.wikipedia.org/wiki/Aave)  
19. [Etherscan — Token AAVE](https://etherscan.io/token/0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDAE9)  
20. [Foro de gobernanza de Aave](https://governance.aave.com)  
21. API de DefiLlama: `/protocol/aave`, `/protocols`, `/summary/fees/aave`, `coins.llama.fi`, `stablecoins.llama.fi` (extracción de gráficos 2026-09-07)

---

*Versión del informe: 7 September 2026 (Asia/Shanghai). Carpeta de gráficos: `charts/`. No use este texto para actividad ilegal ni manipulación de mercado.*
