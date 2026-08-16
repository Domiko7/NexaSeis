<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource, type MapGeoJSONFeature, type MapMouseEvent } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { EMSCFeature, EMSCGeoJSON, Station, StationDataMap } from "../types";
import { getColorMmi, getColorShindo, getNumericIntensityMMI, getNumericIntensityShindo, getTextColorMmi, getTextColorShindo, pgaPgvToMmi, pgvToColor, pgvToShindo } from "../utils/transform";
import StationVisualizer from "./StationVisualizer.vue";

const STATIONS_URL = "https://api-nexaseis.domiko.dev/stations";
const EMSC_URL = "https://www.seismicportal.eu/fdsnws/event/1/query?limit=2500&minmag=3&format=json";
const OPENFREEMAP_STYLE = "https://tiles.openfreemap.org/styles/fiord";
const mapElement = ref<HTMLElement>();
const stations = ref<StationDataMap>({});
const earthquakes = ref<EMSCFeature[]>([]);
const selectedStationKey = ref<string>();
const selectedChannel = ref<string>();
const selectedEarthquakeId = ref<string>();
let map: MapLibreMap | undefined;
let stationMarkers: Marker[] = [];
let stationTimer: number | undefined;
let earthquakeTimer: number | undefined;

const selectedStation = computed<Station | undefined>(() => selectedStationKey.value ? stations.value[selectedStationKey.value] : undefined);
const selectedEarthquake = computed(() => earthquakes.value.find((earthquake) => earthquake.id === selectedEarthquakeId.value));
const availableChannels = computed(() => Object.keys(selectedStation.value?.channels ?? {}).sort());
const activeChannel = computed(() => {
  const station = selectedStation.value;
  if (!station) return undefined;
  return selectedChannel.value && station.channels?.[selectedChannel.value] ? selectedChannel.value : station.station.channel;
});
const displayedStation = computed(() => {
  const station = selectedStation.value;
  return station && activeChannel.value ? station.channels?.[activeChannel.value] ?? station : station;
});
const mmi = computed(() => pgaPgvToMmi(displayedStation.value?.pga ?? 0, displayedStation.value?.pgv ?? 0));
const shindo = computed(() => pgvToShindo(displayedStation.value?.pgv ?? 0));

const closePanel = () => {
  selectedStationKey.value = undefined;
  selectedEarthquakeId.value = undefined;
};

const renderStations = () => {
  if (!map) return;
  stationMarkers.forEach((marker) => marker.remove());
  stationMarkers = Object.entries(stations.value).map(([key, item]) => {
    const element = document.createElement("button");
    element.className = "station-marker";
    element.type = "button";
    element.ariaLabel = item.station.name;
    element.innerHTML = `<svg viewBox="0 0 24 24" width="28" height="28" fill="${pgvToColor(item.pgv)}" stroke="#fff" stroke-width="1.5"><polygon points="12,2 22,20 2,20" /></svg>`;
    element.addEventListener("click", (event) => {
      event.stopPropagation();
      selectedEarthquakeId.value = undefined;
      selectedStationKey.value = key;
      selectedChannel.value = item.station.channel;
    });
    return new Marker({ element, anchor: "center" }).setLngLat([item.station.lon, item.station.lat]).addTo(map!);
  });
};

const earthquakeGeoJson = (): FeatureCollection<Point> => ({
  type: "FeatureCollection",
  features: earthquakes.value.map((earthquake) => ({
    type: "Feature",
    id: earthquake.id,
    geometry: { type: "Point", coordinates: earthquake.geometry.coordinates.slice(0, 2) },
    properties: { id: earthquake.id, magnitude: earthquake.properties.mag },
  })),
});

const renderEarthquakes = () => {
  const source = map?.getSource("earthquakes") as GeoJSONSource | undefined;
  source?.setData(earthquakeGeoJson());
};

const selectEarthquake = (event: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
  const id = event.features?.[0]?.properties?.id;
  if (typeof id !== "string") return;
  selectedStationKey.value = undefined;
  selectedEarthquakeId.value = id;
};

const fetchStations = async () => {
  try {
    const response = await fetch(STATIONS_URL);
    if (response.ok) stations.value = await response.json() as StationDataMap;
  } catch (error) { console.error(error); }
};
const fetchEarthquakes = async () => {
  try {
    const response = await fetch(EMSC_URL);
    if (!response.ok) return;
    const data = await response.json() as EMSCGeoJSON;
    if (Array.isArray(data.features)) earthquakes.value = data.features;
  } catch (error) { console.error(error); }
};

watch(stations, renderStations);
watch(earthquakes, renderEarthquakes);
onMounted(() => {
  map = new MapLibreMap({
    container: mapElement.value!,
    style: OPENFREEMAP_STYLE,
    center: [13.404954, 52.520008],
    zoom: 3,
    minZoom: 2.5,
  });
  map.addControl(new NavigationControl(), "top-left");
  map.on("load", () => {
    map!.addSource("earthquakes", { type: "geojson", data: earthquakeGeoJson() });
    map!.addLayer({
      id: "earthquake-circles",
      type: "circle",
      source: "earthquakes",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["get", "magnitude"], 3, 4, 5, 8, 7, 14],
        "circle-color": ["step", ["get", "magnitude"], "#388E3C", 4, "#FBC02D", 5, "#F57C00", 6, "#D32F2F", 7, "#B71C1C"],
        "circle-stroke-color": ["step", ["get", "magnitude"], "#388E3C", 4, "#FBC02D", 5, "#F57C00", 6, "#D32F2F", 7, "#B71C1C"],
        "circle-stroke-width": 2,
        "circle-opacity": 0.25,
      },
    });
    map!.on("click", "earthquake-circles", selectEarthquake);
    map!.on("mouseenter", "earthquake-circles", () => { map!.getCanvas().style.cursor = "pointer"; });
    map!.on("mouseleave", "earthquake-circles", () => { map!.getCanvas().style.cursor = ""; });
    renderEarthquakes();
    renderStations();
  });
  map.on("click", (event: MapMouseEvent) => {
    if (map!.queryRenderedFeatures(event.point, { layers: ["earthquake-circles"] }).length === 0) closePanel();
  });
  void fetchStations();
  void fetchEarthquakes();
  stationTimer = window.setInterval(fetchStations, 1000);
  earthquakeTimer = window.setInterval(fetchEarthquakes, 60000);
});
onBeforeUnmount(() => {
  window.clearInterval(stationTimer);
  window.clearInterval(earthquakeTimer);
  stationMarkers.forEach((marker) => marker.remove());
  map?.remove();
});
</script>

<template>
  <main class="map-page-container">
    <div ref="mapElement" class="map-wrapper maplibre-map-view" />
    <aside class="side-panel" :class="{ open: selectedStation || selectedEarthquake }">
      <div v-if="selectedStation && selectedStationKey" class="side-panel-content">
        <div class="side-panel-header"><h2 class="side-panel-title">{{ selectedStation.station.name }}</h2><button class="side-panel-close-btn" aria-label="Close" @click="selectedStationKey = undefined">✕</button></div>
        <div class="side-panel-subtitle">{{ selectedStation.station.network }}.{{ selectedStation.station.code }}</div>
        <select v-if="availableChannels.length > 1" v-model="selectedChannel" class="side-panel-channel-select" aria-label="Channel"><option v-for="channel in availableChannels" :key="channel" :value="channel">{{ channel }}</option></select>
        <StationVisualizer v-if="activeChannel" :station-key="selectedStationKey" :location="selectedStation.station.location" :channel="activeChannel" />
        <div class="side-panel-signal-meta">
          <div><span><small>Data stream</small><strong>{{ selectedStation.station.network }}.{{ selectedStation.station.code }}.{{ selectedStation.station.location }}.{{ activeChannel }}</strong></span></div>
        </div>
        <h3 class="side-panel-section-title">Ground motion</h3>
        <div class="side-panel-data-list">
          <div class="side-panel-data-row"><strong>Acceleration</strong><span>{{ ((displayedStation?.pga ?? 0) * 1_000_000).toFixed(2) }} μm/s²</span></div>
          <div class="side-panel-data-row"><strong>Velocity</strong><span>{{ ((displayedStation?.pgv ?? 0) * 1_000_000).toFixed(2) }} μm/s</span></div>
          <div class="side-panel-data-row"><strong>Displacement</strong><span>{{ ((displayedStation?.pgd ?? 0) * 1_000_000).toFixed(2) }} μm</span></div>
        </div>
        <h3 class="side-panel-section-title">Seismic intensity</h3>
        <div class="side-panel-intensity">
          <div class="side-panel-intensity-box"><span class="side-panel-intensity-label-text">MMI</span><span class="side-panel-intensity-label" :style="{ backgroundColor: getColorMmi(mmi), color: getTextColorMmi(mmi) }">{{ getNumericIntensityMMI(mmi) }}</span></div>
          <div class="side-panel-intensity-box"><span class="side-panel-intensity-label-text">JMA</span><span class="side-panel-intensity-label" :style="{ backgroundColor: getColorShindo(shindo), color: getTextColorShindo(shindo) }">{{ getNumericIntensityShindo(shindo) }}</span></div>
        </div>
        <hr class="side-panel-divider">
        <h3 class="side-panel-section-title">More data</h3>
        <a v-for="type in ['raw', 'standard', 'teleseismic']" :key="type" class="side-panel-btn" target="_blank" rel="noopener noreferrer" :href="`https://api-nexaseis.domiko.dev/helicorder/${selectedStation.station.network}/${selectedStation.station.code}/${selectedStation.station.location}/${activeChannel}?type=${type}`">{{ type }} helicorder</a>
      </div>
      <div v-else-if="selectedEarthquake" class="side-panel-content">
        <div class="side-panel-header"><h2 class="side-panel-title">{{ selectedEarthquake.properties.flynn_region || 'Earthquake' }}</h2><button class="side-panel-close-btn" aria-label="Close" @click="selectedEarthquakeId = undefined">✕</button></div>
        <div class="side-panel-subtitle">Event ID: {{ selectedEarthquake.properties.source_id || selectedEarthquake.id }}</div>
        <h3 class="side-panel-section-title">Event details</h3>
        <div class="side-panel-data-list">
          <div class="side-panel-data-row"><strong>Magnitude:</strong><span>{{ selectedEarthquake.properties.magtype.toUpperCase() }}{{ selectedEarthquake.properties.mag }}</span></div>
          <div class="side-panel-data-row"><strong>Depth:</strong><span>{{ selectedEarthquake.properties.depth }} km</span></div>
          <div class="side-panel-data-row"><strong>Time:</strong><span>{{ new Date(selectedEarthquake.properties.time).toLocaleString() }}</span></div>
          <div class="side-panel-data-row"><strong>Coordinates:</strong><span>{{ selectedEarthquake.properties.lat.toFixed(2) }}°, {{ selectedEarthquake.properties.lon.toFixed(2) }}°</span></div>
          <div class="side-panel-data-row"><strong>Source:</strong><span>EMSC[{{ selectedEarthquake.properties.auth }}]</span></div>
        </div>
      </div>
    </aside>
  </main>
</template>
