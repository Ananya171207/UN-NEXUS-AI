import { useEffect } from 'react';
import L from 'leaflet';
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from 'react-leaflet';
import { WORLD_VIEW } from '../../data/taxonomy';
import 'leaflet/dist/leaflet.css';
import './WorldMap.css';

// Map pins are small HTML elements so they can be animated with CSS
// (high and critical events pulse).
const iconCache = new window.Map();
function pinIcon(severity, selected) {
  const key = `${severity}-${selected}`;
  if (!iconCache.has(key)) {
    iconCache.set(
      key,
      L.divIcon({
        className: 'pin-wrap',
        html: `<span class="pin pin-${severity} ${selected ? 'pin-selected' : ''}"><i class="pin-ring"></i><i class="pin-dot"></i></span>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        tooltipAnchor: [0, -10],
      })
    );
  }
  return iconCache.get(key);
}

// Glides the map to a new view whenever `view` changes.
function MapFocus({ view }) {
  const map = useMap();
  const [lat, lng] = view.center;
  const zoom = view.zoom;

  useEffect(() => {
    const here = map.getCenter();
    const alreadyThere =
      Math.abs(here.lat - lat) < 1e-6 && Math.abs(here.lng - lng) < 1e-6 && map.getZoom() === zoom;
    if (!alreadyThere) map.flyTo([lat, lng], zoom, { duration: 1.1 });
  }, [lat, lng, zoom, map]);

  return null;
}

// Reusable world map.
//   markers:    [{ id, position: [lat, lng], severity, tooltip }]
//   selectedId: id of the highlighted marker (or null)
//   onSelect:   called with a marker id, or null when the selected one is clicked again
//   view:       { center: [lat, lng], zoom } the map should show
export default function WorldMap({ markers, selectedId, onSelect, view = WORLD_VIEW }) {
  return (
    <MapContainer
      center={view.center}
      zoom={view.zoom}
      minZoom={2}
      scrollWheelZoom={false}
      worldCopyJump
      className="world-map"
    >
      {/* Free OpenStreetMap tiles. WorldMap.css darkens them to match the theme. */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapFocus view={view} />

      {markers.map((marker) => (
        <Marker
          key={marker.id}
          position={marker.position}
          icon={pinIcon(marker.severity, marker.id === selectedId)}
          eventHandlers={{ click: () => onSelect(marker.id === selectedId ? null : marker.id) }}
        >
          <Tooltip direction="top">{marker.tooltip}</Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
