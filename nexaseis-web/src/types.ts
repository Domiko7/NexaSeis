export interface MarkerData {
  id: string;
  name: string;
  lng: number;
  lat: number;
  color: string;
}

export interface TriangleMarkerProps {
  longitude: number;
  latitude: number;
  color?: string;
  size?: number;
  onClick?: () => void;
}

export interface StationInfo {
  code: string;
  network: string;
  channel: string;
  location: string;
  sensitivity: number;
  name: string;
  lat: number;
  lon: number;
}

export interface Station {
  timestamp: number;
  station: StationInfo;
  pgv: number;
  pga: number;
  pgd: number;
  channels?: Record<string, StationChannel>;
}

export interface StationChannel {
  timestamp: number;
  station: StationInfo;
  pgv: number;
  pga: number;
  pgd: number;
}

export interface WebsocketStation {
  timestamp: number;
  station: StationInfo;
  pgv: number;
  pga: number;
  pgd: number;
  waveform: number[];
  acceleration: number[];
  velocity: number[];
  displacement: number[];
}

export interface StationDataMap {
  [stationKey: string]: Station;
}

export interface StationData {
  stations: Station[];
}

export interface EMSCFeatureProperties {
  source_id: string;
  source_catalog: string;
  time: string;
  flynn_region: string;
  lat: number;
  lon: number;
  depth: number;
  evtype: string;
  auth: string;
  mag: number;
  magtype: string;
}

export interface EMSCFeature {
  type: "Feature";
  id: string;
  geometry: {
    type: "Point";
    coordinates: [number, number, number];
  };
  properties: EMSCFeatureProperties;
}

export interface EMSCGeoJSON {
  type: "FeatureCollection";
  features: EMSCFeature[];
}

export interface EarthquakeMarkerProps {
  longitude: number;
  latitude: number;
  magnitude: number;
  onClick?: () => void;
}
