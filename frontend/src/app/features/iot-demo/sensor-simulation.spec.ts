import { advanceSensorSample } from './sensor-simulation';

describe('advanceSensorSample', () => {
  it('confirms occupation only after five consecutive readings above the high threshold', () => {
    let occupiedReadings = 0;
    let result = advanceSensorSample(150, false, occupiedReadings, 0);
    occupiedReadings = result.occupiedReadings;
    expect(result.transition).toBeNull();

    for (let reading = 0; reading < 3; reading++) {
      result = advanceSensorSample(150, false, occupiedReadings, 0);
      occupiedReadings = result.occupiedReadings;
    }
    expect(result.transition).toBeNull();

    result = advanceSensorSample(150, false, occupiedReadings, 0);
    expect(result.transition).toBe('occupied');
  });

  it('uses hysteresis and does not release while load remains above the low threshold', () => {
    const result = advanceSensorSample(51, true, 0, 3);
    expect(result.transition).toBeNull();
    expect(result.freeReadings).toBe(0);
  });

  it('confirms release after five consecutive readings at or below the low threshold', () => {
    let freeReadings = 0;
    let result = advanceSensorSample(50, true, 0, freeReadings);
    freeReadings = result.freeReadings;
    for (let reading = 0; reading < 3; reading++) {
      result = advanceSensorSample(50, true, 0, freeReadings);
      freeReadings = result.freeReadings;
    }
    expect(result.transition).toBeNull();
    result = advanceSensorSample(50, true, 0, freeReadings);
    expect(result.transition).toBe('free');
  });

  it('resets the occupation debounce when force drops below the threshold', () => {
    const result = advanceSensorSample(149, false, 3, 0);
    expect(result.transition).toBeNull();
    expect(result.occupiedReadings).toBe(0);
  });
});
