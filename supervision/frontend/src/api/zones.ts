import { requestJson } from "./client";
import type { ZoneConfig } from "../types/zoneConfig";

export function getZones() {
  return requestJson<ZoneConfig[]>("/api/zones");
}

export function updateZones(zones: ZoneConfig[]) {
  return requestJson<ZoneConfig[]>("/api/zones", {
    method: "PUT",
    body: JSON.stringify(zones)
  });
}
