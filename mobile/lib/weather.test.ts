import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_CITY,
  cityFromTimeZone,
  describeCode,
  fetchWeather,
  forecastUrl,
  geocodeUrl,
  resolveCity,
  toSnapshot,
} from "./weather";

describe("describeCode", () => {
  it("maps known codes and switches icon by day/night", () => {
    expect(describeCode(0, true)).toEqual({ description: "Clear", icon: "☀️" });
    expect(describeCode(0, false)).toEqual({ description: "Clear", icon: "🌙" });
    expect(describeCode(95, true).description).toBe("Thunderstorm");
  });

  it("keeps an unmapped code visibly unknown rather than defaulting to Clear", () => {
    expect(describeCode(7).description).toBe("Unavailable");
    expect(describeCode(null).description).toBe("Unavailable");
    expect(describeCode(undefined).description).toBe("Unavailable");
  });
});

describe("cityFromTimeZone", () => {
  it("extracts the city and un-escapes underscores", () => {
    expect(cityFromTimeZone("Asia/Riyadh")).toBe("Riyadh");
    expect(cityFromTimeZone("America/New_York")).toBe("New York");
    expect(cityFromTimeZone("America/Argentina/Buenos_Aires")).toBe("Buenos Aires");
  });

  it("returns null for zones that do not name a city", () => {
    expect(cityFromTimeZone("UTC")).toBeNull();
    expect(cityFromTimeZone("Etc/GMT+3")).toBeNull();
    expect(cityFromTimeZone("US/Pacific")).toBeNull();
    expect(cityFromTimeZone("")).toBeNull();
    expect(cityFromTimeZone(null)).toBeNull();
  });
});

describe("resolveCity", () => {
  it("prefers an explicit override", () => {
    expect(resolveCity("Doha", "Asia/Riyadh")).toBe("Doha");
  });

  it("ignores a blank override", () => {
    expect(resolveCity("   ", "Asia/Riyadh")).toBe("Riyadh");
    expect(resolveCity(undefined, "Asia/Riyadh")).toBe("Riyadh");
  });

  it("falls back to the default when the timezone names no city", () => {
    expect(resolveCity(undefined, "UTC")).toBe(DEFAULT_CITY);
  });
});

describe("url builders", () => {
  it("encodes multi-word city names", () => {
    expect(geocodeUrl("New York")).toContain("name=New%20York");
  });

  it("requests one day, auto timezone, and the fields the tile renders", () => {
    const url = forecastUrl(24.71, 46.68);
    expect(url).toContain("latitude=24.71");
    expect(url).toContain("timezone=auto");
    expect(url).toContain("forecast_days=1");
    expect(url).toContain("temperature_2m");
    expect(url).toContain("weather_code");
  });
});

const PAYLOAD = {
  current: {
    temperature_2m: 42.7,
    apparent_temperature: 39.3,
    is_day: 1,
    weather_code: 3,
  },
  daily: { temperature_2m_max: [45.0], temperature_2m_min: [36.0] },
};

describe("toSnapshot", () => {
  it("rounds temperatures and resolves the description", () => {
    const snap = toSnapshot("Riyadh", PAYLOAD)!;
    expect(snap).toMatchObject({
      city: "Riyadh",
      temperature: 43,
      apparentTemperature: 39,
      description: "Overcast",
      high: 45,
      low: 36,
      isDay: true,
    });
  });

  it("uses the night icon when is_day is 0", () => {
    const snap = toSnapshot("Riyadh", {
      ...PAYLOAD,
      current: { ...PAYLOAD.current, is_day: 0, weather_code: 0 },
    })!;
    expect(snap.isDay).toBe(false);
    expect(snap.icon).toBe("🌙");
  });

  it("returns null rather than a partial snapshot when temperature is missing", () => {
    expect(toSnapshot("Riyadh", { current: {} })).toBeNull();
    expect(toSnapshot("Riyadh", {})).toBeNull();
    expect(toSnapshot("Riyadh", null)).toBeNull();
  });

  it("tolerates a missing daily block", () => {
    const snap = toSnapshot("Riyadh", { current: PAYLOAD.current })!;
    expect(snap.temperature).toBe(43);
    expect(snap.high).toBeNull();
    expect(snap.low).toBeNull();
  });

  it("falls back to the actual temperature when apparent is absent", () => {
    const snap = toSnapshot("Riyadh", {
      current: { temperature_2m: 20.4, is_day: 1, weather_code: 0 },
    })!;
    expect(snap.apparentTemperature).toBe(20);
  });
});

describe("fetchWeather", () => {
  function jsonResponse(body: unknown, ok = true, status = 200) {
    return { ok, status, json: async () => body } as Response;
  }

  it("geocodes then fetches the forecast for the resolved coordinates", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ results: [{ name: "Riyadh", latitude: 24.71, longitude: 46.68 }] }),
      )
      .mockResolvedValueOnce(jsonResponse(PAYLOAD));

    const snap = await fetchWeather("Riyadh", fetchImpl as unknown as typeof fetch);

    expect(snap.city).toBe("Riyadh");
    expect(snap.temperature).toBe(43);
    expect(fetchImpl.mock.calls[1][0]).toContain("latitude=24.71");
  });

  it("throws a named error when the city cannot be resolved", async () => {
    const fetchImpl = vi.fn().mockResolvedValueOnce(jsonResponse({ results: [] }));
    await expect(fetchWeather("Zzz", fetchImpl as unknown as typeof fetch)).rejects.toThrow(
      'No location found for "Zzz"',
    );
  });

  it("throws when the forecast call fails", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ results: [{ name: "Riyadh", latitude: 1, longitude: 2 }] }),
      )
      .mockResolvedValueOnce(jsonResponse({}, false, 503));
    await expect(fetchWeather("Riyadh", fetchImpl as unknown as typeof fetch)).rejects.toThrow(
      "HTTP 503",
    );
  });

  it("throws rather than returning a half-built snapshot", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ results: [{ name: "Riyadh", latitude: 1, longitude: 2 }] }),
      )
      .mockResolvedValueOnce(jsonResponse({ current: {} }));
    await expect(fetchWeather("Riyadh", fetchImpl as unknown as typeof fetch)).rejects.toThrow(
      "incomplete",
    );
  });
});
