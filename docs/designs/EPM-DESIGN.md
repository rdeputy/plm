# DAE Engine Performance Monitor (EPM) — System Design

**Document ID:** PLM-DES-001
**Version:** 0.1.0
**Date:** 2026-02-05
**Author:** Reid Deputy / Claude
**Status:** Draft — Concept Design

---

## 1. Purpose

Design an engine performance monitoring system for piston aircraft that matches or exceeds the capabilities of the JP Instruments EDM-930 Primary at a fraction of the cost, with modern connectivity and analytics that the EDM-930 lacks entirely.

**Target market:** Experimental/homebuilt aircraft (E-AB, E-LSA). Secondary: supplemental monitor for certified aircraft alongside existing gauges.

---

## 2. Competitive Baseline — JP Instruments EDM-930

**Price:** $6,800-$8,100 (certified, with probes)

| Capability | EDM-930 | Limitation |
|---|---|---|
| Sampling | 4 Hz (4x/sec) | Adequate but not fast |
| Display | 5.5" VGA TFT, non-touch | Fixed form factor |
| Data logging | 800 hrs (USB stick) | Proprietary format, manual transfer |
| Connectivity | USB only | No WiFi, BT, cloud |
| Analytics | EZTrends desktop app | Dated software, no predictions |
| Leaning | LeanFind (peak detect) | Good, but single-mode |
| Sharing | None | Pilot must carry USB stick to mechanic |
| Cert | TSO/STC (SA01435SE) | Advantage for certified aircraft |

**Reference:** https://www.jpinstruments.com/shop/edm-930-primary/

---

## 3. System Architecture

### 3.1 Two-Board Design

The system uses physically separate sensor acquisition and display/processing boards connected via CAN bus. This provides electrical isolation, flexible mounting, and independent upgrade paths.

```
+--------------------------------------------------+
|                SENSOR BOARD (SAU)                 |
|            STM32G4 + MAX31856 x 12               |
|                                                  |
|  K-type TC --> 6x EGT (0.15% accuracy)          |
|  K-type TC --> 6x CHT                           |
|  Pressure  --> Oil PSI, Fuel PSI, MAP            |
|  RTD/NTC   --> Oil Temp, OAT, Carb Temp          |
|  Hall/Mag  --> RPM (dual pickup redundancy)       |
|  Flow      --> Fuel Flow (Red Cube / FloScan)     |
|  Analog    --> Volts, Amps (x2 for twin bus)     |
|  CAN 2.0B  --> Rotax/Lycoming EFI native data    |
|                                                  |
|  Sampling: 10 Hz all channels, 100 Hz RPM        |
|  Output: CAN bus to Display Unit                 |
|  Power: 7-32V input, reverse polarity protected  |
+-------------------------+------------------------+
                          | CAN bus (shielded twisted pair)
+-------------------------v------------------------+
|              DISPLAY UNIT (DPU)                   |
|         ESP32-S3 + Raspberry Pi CM4               |
|                                                  |
|  +--------------------------------------------+ |
|  |  7" IPS Touchscreen (1024x600)              | |
|  |  Real-time gauges, bar graphs, trends       | |
|  |  Touch-driven leaning assistant             | |
|  |  Configurable layouts (cruise/climb/        | |
|  |  leaning/diagnostic modes)                  | |
|  +--------------------------------------------+ |
|                                                  |
|  Storage: 256GB NVMe -- 10,000+ flight hours     |
|  WiFi: 2.4/5 GHz (Stratux, tablet, cloud sync)  |
|  BLE: Tablet/phone companion app                 |
|  USB-C: Direct data export, firmware update      |
|  GPS: u-blox M10 (position/track/altitude)       |
|  SD slot: Backup/portable export                 |
+--------------------------------------------------+
```

### 3.2 Sensor Board Detail

**Microcontroller:** STM32G474RE
- ARM Cortex-M4F, 170 MHz, FPU
- 3x CAN-FD peripherals (one for display, one for Rotax ECU, one spare)
- 5x 12-bit ADC (up to 4 Msps aggregate)
- Hardware math accelerator (CORDIC, FMAC)

**Thermocouple Interface:** MAX31856 (x12)
- 19-bit resolution, 0.0078 deg C
- +/- 0.15% voltage measurement accuracy
- Built-in cold-junction compensation
- Fault detection (open, short-to-GND, short-to-VCC)
- SPI interface, daisy-chainable via chip-select mux

**Pressure Sensors:**
- Honeywell PX2 series (0-100 PSI, 0-15 PSI ranges)
- 0.25% FSS accuracy, ratiometric output
- Separate transducers for oil, fuel, and manifold pressure

**RPM Sensing:**
- Dual hall-effect or magnetic pickup (redundancy)
- Hardware timer capture on STM32 (sub-microsecond resolution)
- Supports 1, 2, or 4 pulses per revolution (configurable)

**Fuel Flow:**
- Compatible with Red Cube (Electronics International) or FloScan transducers
- Pulse counting via hardware timer

**Voltage/Current:**
- Voltage divider (battery bus, avionics bus)
- 100A shunt with differential amplifier (x2 for split bus)

### 3.3 Display Unit Detail

**Processing:** Raspberry Pi Compute Module 4
- Quad-core ARM Cortex-A72, 1.5 GHz
- 4GB RAM, 32GB eMMC (OS/app) + 256GB NVMe (data)
- Hardware video decode for smooth gauge rendering

**Communications:** ESP32-S3 (coprocessor)
- WiFi 802.11 b/g/n (2.4/5 GHz)
- Bluetooth 5.0 LE
- Handles all wireless I/O, offloading Pi for display

**Display:** 7" IPS capacitive touchscreen
- 1024x600 resolution, 800 nit brightness (sunlight readable)
- Multi-touch for pinch/zoom on trend graphs
- Auto-dimming via ambient light sensor

**GPS:** u-blox MAX-M10S
- 1 Hz position update (configurable to 10 Hz)
- Provides ground speed for fuel planning, track logging

---

## 4. Sensor Specifications vs EDM-930

| Parameter | EDM-930 | EPM Design | Advantage |
|---|---|---|---|
| EGT channels | 6 | 6 (expandable to 12) | Same + twin support |
| CHT channels | 6 | 6 (expandable to 12) | Same + twin support |
| TC chip accuracy | Unknown (proprietary) | +/- 0.15% (MAX31856) | Documented, superior |
| TC resolution | 1 deg F | 0.014 deg F (19-bit) | 70x finer |
| Sample rate (all ch) | 4 Hz | 10 Hz | 2.5x faster |
| RPM sample rate | 4 Hz | 100 Hz | 25x faster |
| ADC resolution | Unknown | 19-bit (TC), 12-bit (analog) | Higher dynamic range |
| Fuel flow | FloScan | Red Cube or FloScan | Compatible with both |
| CAN bus | None | CAN 2.0B / CAN-FD native | Rotax 912iS/915iS direct |
| Redundant RPM | No | Dual pickup | Safety margin |
| GPS | External interface only | Integrated u-blox M10 | Self-contained |

---

## 5. Software Architecture

### 5.1 On-Device Stack

```
+--------------- On-Device (Pi CM4) ----------------+
|                                                    |
|  +----------+  +-----------+  +--------------+    |
|  | CAN Rx   |->| Engine    |->| Display      |    |
|  | Driver   |  | State     |  | Renderer     |    |
|  | (10 Hz)  |  | Machine   |  | (Qt6/QML)    |    |
|  +----------+  +-----+-----+  +--------------+    |
|                       |                            |
|  +--------------------v-----------------------+    |
|  |          Analytics Engine                  |    |
|  |  - LeanAssist (peak detect + ROP/LOP)     |    |
|  |  - Shock cooling monitor (all cyl)         |    |
|  |  - CHT spread analysis                     |    |
|  |  - Trend detection (per-flight + long)     |    |
|  |  - Anomaly flagging (EGT deviation)        |    |
|  |  - Fuel planning (GPS ground speed)        |    |
|  |  - %HP calculation (MAP + RPM + OAT)       |    |
|  +--------------------------------------------+    |
|                                                    |
|  +----------+  +-----------+  +--------------+    |
|  | Flight   |  | WiFi/BLE  |  | Alert        |    |
|  | Recorder |  | Server    |  | Manager      |    |
|  | (SQLite) |  | (REST API)|  | (visual +    |    |
|  |          |  |           |  |  audio)      |    |
|  +----------+  +-----------+  +--------------+    |
+----------------------------------------------------+
         |                    |
         v                    v
+----------------+  +---------------------+
|  Cloud Sync    |  |  Companion App      |
|  (post-flight) |  |  (tablet/phone)     |
|  - Flight log  |  |  - Mirror display   |
|  - Trend DB    |  |  - Passenger view   |
|  - Share w/    |  |  - Post-flight      |
|    mechanic    |  |    review           |
+----------------+  +---------------------+
```

### 5.2 Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Sensor firmware | C / Rust (RTIC) on STM32 | Bare metal, deterministic timing |
| CAN protocol | Custom lightweight frames | Low latency, high reliability |
| Display application | Qt6 / QML on Linux | Hardware-accelerated 2D, touch support |
| On-device data store | SQLite | Proven, zero-config, crash-safe |
| WiFi/BLE coprocessor | ESP-IDF on ESP32-S3 | Offload wireless from display CPU |
| Cloud backend | Supabase (PostgreSQL + Auth) | Leverages existing DAE infrastructure |
| Companion app | React Native (iOS/Android) | Cross-platform, shared codebase |
| Post-flight web dashboard | Next.js | Existing SAAPA/DAE pattern |
| Trend analytics | Python (NumPy/SciPy) | Cloud-side, per-engine trending |

### 5.3 Display Modes

| Mode | Layout | Use Case |
|---|---|---|
| **Cruise** | All cylinders bar graph + fuel state + GPS groundspeed | Normal flight |
| **Climb** | CHT emphasis, shock cooling monitor, oil temp/press | Departure, go-around |
| **Lean** | Full-screen EGT bars with peak markers, fuel flow, %HP | Mixture management |
| **Diagnostic** | All params numeric, CAN bus raw data, probe health | Troubleshooting |
| **Custom** | Drag-and-drop gauge layout editor via touch | Pilot preference |

### 5.4 LeanAssist (vs JPI LeanFind)

JPI LeanFind identifies first and last cylinder to peak. EPM LeanAssist does that plus:

- Real-time ROP/LOP offset guidance with configurable targets (e.g., "50 deg F ROP")
- Calculates and displays GAMI spread automatically
- Stores lean profiles per altitude band for cross-flight trend comparison
- Audible callouts: "Peak on cylinder 3," "All cylinders peaked"
- Historical overlay: shows today's lean vs last 10 flights at same altitude/power

### 5.5 Predictive Analytics (Cloud-Side)

- Per-cylinder EGT/CHT trend analysis across flights at normalized power settings
- Detects gradual probe degradation vs actual engine changes
- Flags anomalies: "CHT #3 trending 15 deg F above 90-day average at this power setting"
- Valve/ring health inference from EGT scatter patterns
- Oil consumption trend (if fuel totalizer + oil level sensor equipped)
- TBO tracking with engine health score

### 5.6 Alert System

| Priority | Visual | Audio | Example |
|---|---|---|---|
| **Critical** | Full red banner, flashing | Continuous tone | CHT > 500 deg F, Oil PSI < 25 |
| **Warning** | Yellow banner | Triple beep | CHT > 400 deg F, EGT spread > 50 deg F |
| **Caution** | Yellow text | Single beep | Shock cooling > 40 deg F/min |
| **Advisory** | White text | None | Fuel < 1 hr remaining |

All alerts are programmable with per-parameter high/low thresholds.

---

## 6. Data Recording

| Feature | EDM-930 | EPM |
|---|---|---|
| Storage capacity | 800 hours | 10,000+ hours (256GB NVMe) |
| Recording rate | 2-60 sec configurable | 100ms (10 Hz) all channels |
| Data format | Proprietary JPI | Open (SQLite + CSV export) |
| Transfer method | USB stick | WiFi auto-sync, USB-C, SD card, cloud |
| Post-flight software | EZTrends (Windows) | Web dashboard (any browser) |
| Data sharing | Manual file transfer | Link-based sharing, mechanic portal |
| Retention | Overwritten when full | Cloud: unlimited |

### 6.1 Flight Record Schema (SQLite)

```sql
-- One row per sample (10 Hz = 36,000 rows/hour)
CREATE TABLE engine_data (
    timestamp_ms   INTEGER PRIMARY KEY,
    flight_id      TEXT NOT NULL,
    egt_1 REAL, egt_2 REAL, egt_3 REAL, egt_4 REAL, egt_5 REAL, egt_6 REAL,
    cht_1 REAL, cht_2 REAL, cht_3 REAL, cht_4 REAL, cht_5 REAL, cht_6 REAL,
    oil_temp REAL, oil_psi REAL,
    fuel_psi REAL, fuel_flow_gph REAL, fuel_remaining_gal REAL,
    map_inhg REAL, rpm INTEGER,
    oat_c REAL, carb_temp_c REAL,
    volts_1 REAL, volts_2 REAL, amps_1 REAL, amps_2 REAL,
    gps_lat REAL, gps_lon REAL, gps_alt_ft REAL, gps_gs_kt REAL,
    hp_pct REAL
);

CREATE TABLE flights (
    flight_id    TEXT PRIMARY KEY,
    start_time   TEXT NOT NULL,
    end_time     TEXT,
    hobbs_start  REAL,
    hobbs_end    REAL,
    fuel_used    REAL,
    alerts       TEXT, -- JSON array of alert events
    notes        TEXT
);

CREATE TABLE alerts_log (
    id           INTEGER PRIMARY KEY,
    flight_id    TEXT NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    severity     TEXT NOT NULL, -- critical/warning/caution/advisory
    parameter    TEXT NOT NULL,
    value        REAL,
    threshold    REAL,
    message      TEXT
);
```

---

## 7. Connectivity

### 7.1 WiFi

- **In-flight:** Connects to Stratux ADS-B receiver WiFi (receive GPS/traffic data)
- **On-ground:** Connects to home/hangar WiFi for automatic cloud sync
- **Hotspot mode:** Acts as AP for tablet companion app when no WiFi available

### 7.2 Bluetooth LE

- Companion app (iOS/Android) connects via BLE
- Real-time gauge mirroring on tablet/phone
- Useful for rear-seat passenger or instructor

### 7.3 Cloud Sync

- Automatic post-shutdown sync when WiFi available
- Compressed flight data upload (typical flight: 5-15 MB)
- Cloud stores full-resolution data indefinitely
- Web dashboard at `epm.dae.tools` (or similar)
- Shareable links: pilot sends mechanic a link to specific flight data

---

## 8. Bill of Materials

| Component | Unit Cost | Qty | Total |
|---|---|---|---|
| STM32G474RE (sensor MCU) | $8 | 1 | $8 |
| MAX31856 TC amplifier breakout | $12 | 12 | $144 |
| Honeywell PX2 pressure transducers | $25 | 3 | $75 |
| RTD/NTC temperature sensors | $8 | 3 | $24 |
| RPM hall-effect sensor | $10 | 2 | $20 |
| Fuel flow transducer (Red Cube) | $120 | 1 | $120 |
| Current shunt (100A) | $15 | 2 | $30 |
| CAN transceiver (MCP2562) | $3 | 2 | $6 |
| Raspberry Pi CM4 (4GB/32GB eMMC) | $65 | 1 | $65 |
| CM4 IO board (custom or Waveshare) | $35 | 1 | $35 |
| 7" IPS touchscreen (1024x600, 800 nit) | $60 | 1 | $60 |
| ESP32-S3-WROOM-1 module | $8 | 1 | $8 |
| u-blox MAX-M10S GPS module | $20 | 1 | $20 |
| K-type thermocouple probes (EGT, bayonet) | $15 | 6 | $90 |
| K-type thermocouple probes (CHT, ring) | $12 | 6 | $72 |
| PCB fabrication (2 boards, 4-layer) | $50 | 1 | $50 |
| Enclosure (CNC aluminum, anodized) | $80 | 1 | $80 |
| Connectors (D-sub, Molex), wiring harness | $60 | 1 | $60 |
| **Total BOM** | | | **~$967** |

**vs EDM-930 at $6,800-$8,100: approximately 85% cost reduction.**

Note: Does not include development time, tooling, or installation labor. Production volume would reduce BOM to ~$600-700 at 100+ units.

---

## 9. Certification Path

| Target | Approach | Estimated Cost | Timeline |
|---|---|---|---|
| **Experimental (E-AB/E-LSA)** | No certification needed | $0 | Immediate |
| **Part 91 supplemental** | Install alongside existing gauges, non-primary | Minimal (field approval) | Months |
| **Primary replacement (TSO)** | DO-160G environmental, DO-178C DAL-D software | $150K-$500K | Years |

**Recommendation:** Launch as experimental/supplemental first. TSO certification is a business decision that only makes sense at production scale (500+ units) or if pursuing the certified market as a product line.

---

## 10. Existing Open-Source Reference Designs

| Project | Platform | Cost | Channels | Status |
|---|---|---|---|---|
| Enguino | Arduino Leonardo | ~$150 | 8 TC + 7 analog | Abandoned (functional) |
| Hackaday Engine Monitor | Raspberry Pi | DIY | 16 channels | Prototype |
| Experimental Avionics EMS | Arduino + LTC2983 | DIY | 8 TC + 8 analog | Active |
| Airduino | Arduino | Low-cost | TBD | Early |

**Key takeaway:** No existing open-source project combines modern display (touchscreen), connectivity (WiFi/BLE/cloud), predictive analytics, and a complete sensor suite. This is the gap EPM fills.

**References:**
- https://github.com/tomcourt/enguino
- https://experimentalavionics.com/engine-management-system/
- https://hackaday.io/project/10363-engine-monitor

---

## 11. Honest Assessment — EDM-930 Advantages

| EDM-930 Strength | EPM Mitigation |
|---|---|
| FAA TSO/STC certified | Target experimental first; supplemental for certified |
| Decades of field reliability data | Extensive bench + flight testing before release |
| Complete kit (probes + harness + display) | Ship complete kits, not bare PCBs |
| Dealer/installer network | Online community, YouTube install guides, A&P partnerships |
| Known brand in GA community | Build reputation through experimental community first |

---

## 12. Implementation Phases

### Phase 1: Sensor Board
- Schematic and PCB layout (KiCad)
- MAX31856 multiplexing and CAN output firmware
- Bench test with thermocouple simulator

### Phase 2: Display Prototype
- Pi CM4 + touchscreen integration
- Qt6/QML gauge rendering engine
- CAN input driver and data pipeline

### Phase 3: Ground Test
- Full system on engine test stand or run-up
- Compare readings against calibrated reference instruments
- Validate all sensor channels end-to-end

### Phase 4: Flight Test
- Install alongside EDM on experimental aircraft
- Record both systems simultaneously
- Compare accuracy, latency, reliability over 50+ hours

### Phase 5: Software Features
- LeanAssist algorithm
- Full data logging and playback
- WiFi sync and companion app
- Alert system tuning

### Phase 6: Cloud and Analytics
- Post-flight web dashboard
- Mechanic sharing portal
- Long-term trend analysis
- Fleet-level analytics (multi-aircraft)

---

## 13. Related Documents

- PLM product structure (TBD)
- Electrical schematic (TBD — Phase 1 deliverable)
- Software requirements specification (TBD — Phase 2 deliverable)
- Test plan (TBD — Phase 3 deliverable)

---

*Document Version: 0.1.0*
*Created: 2026-02-05*
*Status: Draft concept design — not yet reviewed*
