export const SAMPLE_INTERVAL_MS = 250;
export const OCCUPIED_THRESHOLD_G = 150;
export const FREE_THRESHOLD_G = 50;
export const DEBOUNCE_READINGS = 5;
export const MAX_LOAD_G = 2000;

export type SensorTransition = 'occupied' | 'free' | null;

export interface SensorSample {
  occupiedReadings: number;
  freeReadings: number;
  transition: SensorTransition;
}

export function advanceSensorSample(
  loadGrams: number,
  occupied: boolean,
  occupiedReadings: number,
  freeReadings: number,
): SensorSample {
  if (!occupied) {
    const nextOccupiedReadings = loadGrams >= OCCUPIED_THRESHOLD_G ? occupiedReadings + 1 : 0;
    return nextOccupiedReadings >= DEBOUNCE_READINGS
      ? { occupiedReadings: 0, freeReadings: 0, transition: 'occupied' }
      : { occupiedReadings: nextOccupiedReadings, freeReadings: 0, transition: null };
  }

  const nextFreeReadings = loadGrams <= FREE_THRESHOLD_G ? freeReadings + 1 : 0;
  return nextFreeReadings >= DEBOUNCE_READINGS
    ? { occupiedReadings: 0, freeReadings: 0, transition: 'free' }
    : { occupiedReadings: 0, freeReadings: nextFreeReadings, transition: null };
}
