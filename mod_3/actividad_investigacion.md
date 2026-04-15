# Actividad: Investigación Módulo 3

## Instrucciones

En equipos de 2-3 personas investiguen los temas asignados. Cada equipo entrega un reporte escrito y presenta sus hallazgos al grupo en 10-15 minutos. El reporte debe incluir: definición del concepto, cómo funciona, en qué sistemas reales se usa y un ejemplo concreto propio (no copiado de la fuente).

---

## Temas de investigación

### Tema 1 — Teorema CAP y sus implicaciones

1. ¿Qué establece formalmente el Teorema CAP?
2. ¿Por qué la tolerancia a particiones no es opcional en sistemas distribuidos reales?
3. Busca tres sistemas reales (uno CP, uno AP, uno que tenga configuración ajustable) y explica qué sacrifican y en qué escenarios.
4. El teorema CAP fue criticado y refinado. Investiga el modelo **PACELC** (Patterson et al.) y explica en qué mejora al CAP.

---

### Tema 2 — Modelos de consistencia

1. Define y diferencia: linearizabilidad, consistencia secuencial y consistencia causal. ¿En qué casos el orden importa y en cuáles no?
2. ¿Qué son los relojes vectoriales? ¿Qué problema resuelven que los relojes de Lamport no pueden resolver?
3. ¿Qué son las garantías de sesión (*session guarantees*)? Lista las cuatro principales y da un ejemplo de aplicación real para cada una.
4. Busca un incidente real documentado donde la consistencia eventual causó un problema visible para los usuarios (pista: busca los postmortems de Amazon DynamoDB o los análisis de Jepsen).

---

### Tema 3 — Replicación: Primaria-Copia y Multi-Master

1. Explica el modelo Primaria-Copia: roles, flujo de escritura, flujo de lectura.
2. ¿Qué es el split-brain? ¿Cómo lo previene el quórum?
3. Explica el modelo Multi-Master. ¿Qué estrategias existen para resolver conflictos de escritura?
4. Investiga cómo resuelve MySQL Group Replication el problema del split-brain comparado con PostgreSQL streaming replication.

---

### Tema 4 — CRDTs

1. ¿Qué propiedad matemática hace que los CRDTs no tengan conflictos?
2. Explica con un ejemplo propio cómo funciona un **PN-Counter** (incremento y decremento distribuido).
3. Explica el **OR-Set** (Observed-Remove Set): ¿por qué es necesario comparado con un G-Set simple?
4. Busca un sistema de producción que use CRDTs (Riak, Redis, Automerge, etc.) y explica cómo los implementa.

---

### Tema 5 — Two-Phase Commit (2PC)

1. Describe las dos fases del protocolo con un diagrama de mensajes.
2. ¿Por qué se dice que 2PC es un protocolo de bloqueo (*blocking protocol*)? ¿En qué escenario exacto ocurre el bloqueo?
3. Investiga **Three-Phase Commit (3PC)**: ¿qué fase agrega y qué problema del 2PC intenta resolver? ¿Por qué no se usa ampliamente en producción?
4. ¿Cómo maneja PostgreSQL las transacciones distribuidas con 2PC (busca `PREPARE TRANSACTION` en la documentación)?

---

### Tema 6 — Raft

1. Explica los tres sub-problemas que Raft descompone: elección de líder, replicación de log y seguridad.
2. ¿Qué es un **término** (*term*) en Raft? ¿Para qué sirve?
3. Describe el proceso completo de elección de líder: ¿qué pasa si dos candidatos empatan en votos?
4. Busca una implementación real de Raft (etcd, CockroachDB o TiKV) y describe una decisión de diseño que hayan tomado diferente al paper original.

---

### Tema 7 — Paxos

1. Describe las fases Prepare/Promise y Accept/Accepted con un diagrama de mensajes.
2. ¿Qué garantiza el número de propuesta `n`? ¿Por qué un aceptador rechaza propuestas con `n` menor?
3. Paxos básico solo acuerda un único valor. Investiga **Multi-Paxos**: ¿qué optimización introduce para acordar una secuencia de valores?
4. Compara Paxos con Raft: ¿cuáles son las diferencias fundamentales en su diseño? ¿En qué casos se prefiere uno sobre el otro?

---

### Tema 8 — Replicación en bases de datos distribuidas

1. ¿Qué es el WAL (Write-Ahead Log)? ¿Por qué garantiza que la réplica llega exactamente al mismo estado que el primario?
2. Compara replicación por **sentencias** vs. replicación por **filas** (*row-based*): ventajas, desventajas y cuándo cada una falla.
3. ¿Qué es el sharding? Compara sharding por rango vs. sharding por hash: ¿cuándo cada uno genera hotspots?
4. Investiga cómo Cassandra combina replicación y consistencia configurable (busca *replication factor* y *consistency level* en su documentación).

---

## Fuentes recomendadas

### Libros

- **Kleppmann, M.** — *Designing Data-Intensive Applications* (2017, O'Reilly). Capítulos 5 (Replicación), 6 (Particionado) y 9 (Consistencia y Consenso). Es la referencia más accesible del área.
- **Tanenbaum, A. & Van Steen, M.** — *Distributed Systems: Principles and Paradigms* (3a ed.). Capítulos 6 y 7.
- **Coulouris, G. et al.** — *Distributed Systems: Concepts and Design* (5a ed.). Capítulos 15-18.

### Papers originales

- **Brewer, E.** — *Towards Robust Distributed Systems* (2000). Keynote PODC donde se enuncia el Teorema CAP por primera vez.
- **Gilbert, S. & Lynch, N.** — *Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services* (2002, SIGACT News). Demostración formal del CAP.
- **Lamport, L.** — *Time, Clocks, and the Ordering of Events in a Distributed System* (1978, Communications of the ACM). Define los relojes lógicos y la relación "ocurre antes".
- **Lamport, L.** — *Paxos Made Simple* (2001). Explicación informal del algoritmo Paxos por su autor.
- **Ongaro, D. & Ousterhout, J.** — *In Search of an Understandable Consensus Algorithm* (2014, USENIX ATC). Paper original de Raft.
- **Shapiro, M. et al.** — *Conflict-free Replicated Data Types* (2011, INRIA). Paper original de CRDTs.
- **Vogels, W.** — *Eventually Consistent* (2009, Communications of the ACM). Amazon explica su modelo de consistencia para DynamoDB.
- **Patterson, D. et al.** — *PACELC: An Improved Approach to the CAP Theorem* (2012, IEEE Data Engineering Bulletin).

### Recursos en línea

- **Jepsen** (`jepsen.io`) — análisis de consistencia de sistemas distribuidos reales. Documentan bugs encontrados en etcd, Cassandra, MongoDB, Redis y otros.
- **The Paper Trail** (`the-paper-trail.org`) — explicaciones accesibles de papers de sistemas distribuidos.
- **Raft Visualization** (`raft.github.io`) — visualización interactiva del algoritmo Raft en tiempo real.
- Documentación oficial de **etcd**, **CockroachDB**, **Cassandra** y **PostgreSQL** (secciones de replicación y consistencia).
