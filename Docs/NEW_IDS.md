REGEX para IDs: **"^RDB[A-Z]{8}[0-9]{7}$"**

#### Propuesta de Acronimos para Organismos

*Escherichia coli* ➔  **ECOLI**

*Shigella boydii* ➔ **SBOYD**

*Shigella flexneri* ➔ **SFLEX**

*Shigella sonnei* ➔ **SSONN**

| **Organismo**       | **Organism** | **Collection** | **Ejemplo de ID**    |
| ------------------- | ------------ | -------------- | -------------------- |
| *Escherichia coli*  | `SCOLI`     | `ORG`     | **RDBMGECOORG0000001** |
| *Shigella boydii*   | `SBOYD`      | `ORG`          | **RDBSBOYDOR0000001** |
| *Shigella flexneri* | `SFLEX`      | `ORG`          | **RDBSFLEXOR0000001** |
| *Shigella sonnei*   | `SSONN`      | `ORG`          | **RDBSSONNOR0000001** |



[x] Limpiar nombres de org. 

[ ] Verificar la manera en que se usa el metadata de los json para generar IDs

[ ] Listar cuantos IDs se estan generando

Genes
ACRONYM    FILES      COLLECTION_DATA
ECOLI      515        769902
SBOYD      15         37577
SFLEX      16         47898
SSONN      52         91686

Products
ECOLI      514        767188
SBOYD      15         37144
SFLEX      16         47838
SSONN      52         91526

Orgs

ACRONYM    FILES      COLLECTION_DATA
ECOLI      588        588
SBOYD      15         15
SFLEX      16         16
SSONN      52         52



Escherichia coli
Escherichia coli K-12
Escherichia coli O157
Escherichia coli O157:H7
Escherichia coli O104:H4
Escherichia coli O1:H42
Escherichia coli O84:H7
Shigella boydii
Shigella flexneri
Shigella flexneri 1c
Shigella flexneri 3a
Shigella flexneri 5a
Shigella sonnei



## Propuesta

Si quitamos la **`C` final de todos los acrónimos de colección**, entonces quedan todos en **2 letras**, y el formato del ID cambia, ademas de agregar 2 digitos al numero secuencial.

### Estructura

```text
RDBMG ECOLI GN 0000001
│     │     │  └──────── número secuencial
│     │     └─────────── acrónimo de colección
│     └───────────────── acrónimo de organismo
└─────────────────────── RegulonDB Multi-Genomic
```

Así:

```text
RDBMG{ORGANISM_ACRONYM}{COLLECTION_ACRONYM}{SEQUENTIAL_ID}
```

### Regex

Como ahora tenemos:

- **`RDBMG` → 5 caracteres**
- **organismo → 5 letras**
- **colección → 2 letras**
- **secuencial → 7 dígitos**

el regex sería:

```regex
^RDBMG[A-Z]{5}[A-Z]{2}[0-9]{7}$
ó
^RDBMG[A-Z]{7}[0-9]{7}$
```

Por ejemplo:

```text
RDBMGECOLIGN0000001
```

------

## Nuevos acrónimos para las colecciones

Quitando la `C`:

| Colección                 | Actual | Nuevo  |
| ------------------------- | ------ | ------ |
| `evidences`               | EVC    | **EV** |
| `externalCrossReferences` | ERC    | **ER** |
| `genes`                   | GNC    | **GN** |
| `motifs`                  | MTC    | **MT** |
| `operons`                 | OPC    | **OP** |
| `organisms`               | ORG    | **OR** |
| `products`                | PDC    | **PD** |
| `promoters`               | PMC    | **PM** |
| `promoterFeatures`        | PFC    | **PF** |
| `publications`            | PRC    | **PR** |
| `regulatoryComplexes`     | RCC    | **RC** |
| `regulatoryContinuants`   | CNC    | **CN** |
| `regulatoryInteractions`  | RIC    | **RI** |
| `sigmaFactors`            | SFC    | **SF** |
| `terminators`             | TMC    | **TM** |
| `transcriptionFactors`    | TFC    | **TF** |
| `regulatorySites`         | BSC    | **BS** |
| `transcriptionUnits`      | TUC    | **TU** |

Entonces, por ejemplo, para **E. coli**:

```text
RDBMGECOLIEV0000001    # evidences
RDBMGECOLIER0000001    # externalCrossReferences
RDBMGECOLIGN0000001    # genes
RDBMGECOLIMT0000001    # motifs
RDBMGECOLIOP0000001    # operons
RDBMGECOLIOR0000001    # organisms
RDBMGECOLIPD0000001    # products
RDBMGECOLIPM0000001    # promoters
RDBMGECOLIPF0000001    # promoterFeatures
RDBMGECOLIPR0000001    # publications
RDBMGECOLIRC0000001    # regulatoryComplexes
RDBMGECOLICN0000001    # regulatoryContinuants
RDBMGECOLIRI0000001    # regulatoryInteractions
RDBMGECOLISF0000001    # sigmaFactors
RDBMGECOLITM0000001    # terminators
RDBMGECOLITF0000001    # transcriptionFactors
RDBMGECOLIBS0000001    # regulatorySites
RDBMGECOLITU0000001    # transcriptionUnits
```

Y para los otros organismos:

```text
RDBMGSBOYDGN0000001    # Shigella boydii - genes
RDBMGSFLEXGN0000001    # Shigella flexneri - genes
RDBMGSSONNGN0000001    # Shigella sonnei - genes
```

### Una ventaja importante

Ahora tenemos una estructura muy fácil de leer:

```text
RDBMG ECOLI GN 0000001
      └──── ┘
      │     └── Genes
      └──────── E. coli
```

Y `RI`, `TU`, `TF`, etc. son inmediatamente reconocibles.

Con **7 dígitos** tenemos hasta **9,999,999 registros por combinación organismo + colección**.
