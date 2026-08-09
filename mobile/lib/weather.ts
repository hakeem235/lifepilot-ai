/**
 * Open-Meteo weather for the home dashboard tile.
 *
 * Open-Meteo is keyless and public, so this calls it directly rather than
 * proxying through the backend — there is no credential to protect and no
 * per-user cost to meter (unlike the Claude seam, which D12 governs).
 *
 * Location: we have no location permission and adding `expo-location` needs an
 * Advisor Question (dependency rule), so the city is derived from the device
 * timezone — "Asia/Riyadh" -> "Riyadh" — and can be overridden with
 * EXPO_PUBLIC_WEATHER_CITY. That is an approximation, not a fix: see
 * cityFromTimeZone below.
 */

const GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search";
const FORECAST_URL = "https://api.open-meteo.com/v1/forecast";

/** Falls back to this only when the timezone yields nothing usable. */
export const DEFAULT_CITY = "Riyadh";

export type WeatherSnapshot = {
  city: string;
  temperature: number;
  apparentTemperature: number;
  code: number;
  description: string;
  icon: string;
  high: number | null;
  low: number | null;
  isDay: boolean;
};

/** WMO 4677 codes grouped to the granularity a single tile can show. */
const WMO: Record<number, { description: string; day: string; night: string }> = {
  0: { description: "Clear", day: "☀️", night: "🌙" },
  1: { description: "Mainly clear", day: "🌤", night: "🌙" },
  2: { description: "Partly cloudy", day: "⛅️", night: "☁️" },
  3: { description: "Overcast", day: "☁️", night: "☁️" },
  45: { description: "Fog", day: "🌫", night: "🌫" },
  48: { description: "Rime fog", day: "🌫", night: "🌫" },
  51: { description: "Light drizzle", day: "🌦", night: "🌧" },
  53: { description: "Drizzle", day: "🌦", night: "🌧" },
  55: { description: "Heavy drizzle", day: "🌧", night: "🌧" },
  56: { description: "Freezing drizzle", day: "🌧", night: "🌧" },
  57: { description: "Freezing drizzle", day: "🌧", night: "🌧" },
  61: { description: "Light rain", day: "🌦", night: "🌧" },
  63: { description: "Rain", day: "🌧", night: "🌧" },
  65: { description: "Heavy rain", day: "🌧", night: "🌧" },
  66: { description: "Freezing rain", day: "🌧", night: "🌧" },
  67: { description: "Freezing rain", day: "🌧", night: "🌧" },
  71: { description: "Light snow", day: "🌨", night: "🌨" },
  73: { description: "Snow", day: "🌨", night: "🌨" },
  75: { description: "Heavy snow", day: "❄️", night: "❄️" },
  77: { description: "Snow grains", day: "🌨", night: "🌨" },
  80: { description: "Light showers", day: "🌦", night: "🌧" },
  81: { description: "Showers", day: "🌧", night: "🌧" },
  82: { description: "Heavy showers", day: "⛈", night: "⛈" },
  85: { description: "Snow showers", day: "🌨", night: "🌨" },
  86: { description: "Snow showers", day: "🌨", night: "🌨" },
  95: { description: "Thunderstorm", day: "⛈", night: "⛈" },
  96: { description: "Thunderstorm", day: "⛈", night: "⛈" },
  99: { description: "Thunderstorm", day: "⛈", night: "⛈" },
};

/**
 * Describe a WMO code. An unmapped code must stay visibly unknown rather than
 * silently rendering as "Clear" — a wrong-but-plausible tile is worse than a
 * blank one, since the user cannot tell it is wrong.
 */
export function describeCode(
  code: number | null | undefined,
  isDay = true,
): { description: string; icon: string } {
  const entry = code == null ? undefined : WMO[code];
  if (!entry) return { description: "Unavailable", icon: "🌡" };
  return { description: entry.description, icon: isDay ? entry.day : entry.night };
}

/**
 * Derive a city name from an IANA timezone: "America/New_York" -> "New York".
 *
 * This is a heuristic, and deliberately a conservative one. It is correct for
 * city-named zones (the common case) and returns null rather than a guess for
 * region zones like "Europe/London" is fine but "US/Pacific" or "UTC" are not
 * cities. Callers fall back to DEFAULT_CITY. Real device location needs
 * expo-location, which is an Advisor decision, not mine.
 */
export function cityFromTimeZone(timeZone: string | null | undefined): string | null {
  if (!timeZone || !timeZone.includes("/")) return null;
  const parts = timeZone.split("/");
  const last = parts[parts.length - 1];
  if (!last) return null;
  // Zones like "US/Pacific" or "Etc/GMT+3" name a region or offset, not a city.
  if (parts[0] === "Etc" || parts[0] === "US" || /^GMT|^UTC|[+\d]/.test(last)) return null;
  return last.replace(/_/g, " ");
}

/** The city we should ask about: explicit override, else timezone, else default. */
export function resolveCity(
  override: string | undefined,
  timeZone: string | null | undefined,
): string {
  const trimmed = override?.trim();
  if (trimmed) return trimmed;
  return cityFromTimeZone(timeZone) ?? DEFAULT_CITY;
}

export function geocodeUrl(city: string): string {
  return `${GEOCODE_URL}?name=${encodeURIComponent(city)}&count=1&format=json`;
}

export function forecastUrl(latitude: number, longitude: number): string {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    current: "temperature_2m,apparent_temperature,is_day,weather_code",
    daily: "temperature_2m_max,temperature_2m_min",
    timezone: "auto",
    forecast_days: "1",
  });
  return `${FORECAST_URL}?${params.toString()}`;
}

type ForecastPayload = {
  current?: {
    temperature_2m?: number;
    apparent_temperature?: number;
    is_day?: number;
    weather_code?: number;
  };
  daily?: { temperature_2m_max?: number[]; temperature_2m_min?: number[] };
};

/**
 * Shape a raw Open-Meteo payload into the tile's view model.
 *
 * Returns null instead of a partial snapshot when the temperature is missing —
 * a tile reading "—°" with a real-looking description would misrepresent the
 * data as live. The caller renders the error state instead.
 */
export function toSnapshot(city: string, payload: ForecastPayload | null): WeatherSnapshot | null {
  const current = payload?.current;
  if (!current || typeof current.temperature_2m !== "number") return null;

  const isDay = current.is_day !== 0;
  const { description, icon } = describeCode(current.weather_code, isDay);
  const high = payload?.daily?.temperature_2m_max?.[0];
  const low = payload?.daily?.temperature_2m_min?.[0];

  return {
    city,
    temperature: Math.round(current.temperature_2m),
    apparentTemperature: Math.round(
      typeof current.apparent_temperature === "number"
        ? current.apparent_temperature
        : current.temperature_2m,
    ),
    code: current.weather_code ?? -1,
    description,
    icon,
    high: typeof high === "number" ? Math.round(high) : null,
    low: typeof low === "number" ? Math.round(low) : null,
    isDay,
  };
}

/** Fetch a snapshot. Throws on any failure so the hook can show a real error. */
export async function fetchWeather(
  city: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WeatherSnapshot> {
  const geoRes = await fetchImpl(geocodeUrl(city));
  if (!geoRes.ok) throw new Error(`Geocoding failed (HTTP ${geoRes.status})`);
  const place = (await geoRes.json())?.results?.[0];
  if (!place) throw new Error(`No location found for "${city}"`);

  const res = await fetchImpl(forecastUrl(place.latitude, place.longitude));
  if (!res.ok) throw new Error(`Forecast failed (HTTP ${res.status})`);

  const snapshot = toSnapshot(place.name ?? city, await res.json());
  if (!snapshot) throw new Error("Forecast response was incomplete");
  return snapshot;
}
