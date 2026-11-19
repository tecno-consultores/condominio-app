import { describe, expect, it } from 'vitest';
import {
  addDecimalHalfUp,
  compareDecimal,
  divideDecimalHalfUp,
  formatScaledBigInt,
  multiplyDecimalHalfUp,
  parseDecimal,
  roundDecimalHalfUp,
  scaleRoundedHalfUp,
} from './decimal';

describe('Utilidades decimales deterministas ROUND_HALF_UP (decimal.ts)', () => {
  it('parsea cadenas y números válidos rechazando entradas inválidas o infinitas', () => {
    expect(parseDecimal('  +12.345  ')).toEqual({
      negative: false,
      digits: 12345n,
      scale: 3,
    });
    expect(parseDecimal('-0.00')).toEqual({
      negative: false,
      digits: 0n,
      scale: 2,
    });
    expect(parseDecimal('-5.5')).toEqual({
      negative: true,
      digits: 55n,
      scale: 1,
    });
    expect(parseDecimal(null)).toBeNull();
    expect(parseDecimal('')).toBeNull();
    expect(parseDecimal(Number.NaN)).toBeNull();
    expect(parseDecimal(Number.POSITIVE_INFINITY)).toBeNull();
    expect(parseDecimal('12.3.4')).toBeNull();
  });

  it('redondea mitad hacia arriba (ROUND_HALF_UP) evitando sesgo IEEE-754', () => {
    expect(roundDecimalHalfUp('1.005', 2)).toBe('1.01');
    expect(roundDecimalHalfUp('2.675', 2)).toBe('2.68');
    expect(roundDecimalHalfUp('-1.005', 2)).toBe('-1.01');
    expect(roundDecimalHalfUp('1.004', 2)).toBe('1.00');
    expect(roundDecimalHalfUp('42', 2)).toBe('42.00');
    expect(roundDecimalHalfUp('42', 0)).toBe('42');
    expect(roundDecimalHalfUp('invalid', 2)).toBe('0.00');
  });

  it('multiplica y divide con precisión financiera ROUND_HALF_UP', () => {
    expect(multiplyDecimalHalfUp('50.00', '36.50', 2)).toBe('1825.00');
    expect(multiplyDecimalHalfUp('0.1', '0.2', 2)).toBe('0.02');
    expect(multiplyDecimalHalfUp('-1.005', '1', 2)).toBe('-1.01');
    expect(multiplyDecimalHalfUp('bad', '10', 2)).toBe('0.00');

    expect(divideDecimalHalfUp('365.00', '36.50', 2)).toBe('10.00');
    expect(divideDecimalHalfUp('1.005', '1', 2)).toBe('1.01');
    expect(divideDecimalHalfUp('-10.00', '3', 2)).toBe('-3.33');
    expect(divideDecimalHalfUp('100', '0', 2)).toBe('0.00');
    expect(divideDecimalHalfUp('bad', '2', 2)).toBe('0.00');
  });

  it('compara y suma múltiples importes decimales exactamente', () => {
    expect(compareDecimal('50.00', '50')).toBe(0);
    expect(compareDecimal('49.99', '50.00')).toBe(-1);
    expect(compareDecimal('50.01', '50.00')).toBe(1);
    expect(compareDecimal('bad', '10')).toBe(0);

    expect(addDecimalHalfUp(['0.1', '0.2', '1.005'], 2)).toBe('1.31');
    expect(addDecimalHalfUp(['-5.00', '2.00'], 2)).toBe('-3.00');
    expect(addDecimalHalfUp([], 2)).toBe('0.00');
  });

  it('maneja undefined, escalas asimétricas, negativos en b y redondeo negativo en suma', () => {
    expect(parseDecimal(undefined)).toBeNull();
    expect(parseDecimal(Number.NEGATIVE_INFINITY)).toBeNull();
    expect(parseDecimal(-0)).toEqual({ negative: false, digits: 0n, scale: 0 });
    expect(parseDecimal('0')).toEqual({ negative: false, digits: 0n, scale: 0 });

    expect(compareDecimal('-5', '-10')).toBe(1);
    expect(compareDecimal('-10', '-5')).toBe(-1);
    expect(compareDecimal('1', '-2')).toBe(1);
    expect(compareDecimal('-2', '1')).toBe(-1);
    expect(compareDecimal('5', '5.00')).toBe(0);
    expect(compareDecimal('4.9', '4.95')).toBe(-1);
    expect(compareDecimal('5.1', '5.05')).toBe(1);
    expect(compareDecimal(null, '10')).toBe(0);
    expect(compareDecimal('10', undefined)).toBe(0);

    expect(addDecimalHalfUp(['1.50', null, undefined, 'bad', '2.50'], 2)).toBe('4.00');
    expect(addDecimalHalfUp([null, undefined, 'bad'], 2)).toBe('0.00');
    expect(addDecimalHalfUp(['-1.005', '0'], 2)).toBe('-1.01');
    expect(addDecimalHalfUp(['-0.004', '0.004'], 2)).toBe('0.00');

    expect(roundDecimalHalfUp('-0.001', 2)).toBe('0.00');
    expect(multiplyDecimalHalfUp('2', undefined, 2)).toBe('0.00');
    expect(divideDecimalHalfUp('10', null, 2)).toBe('0.00');
    expect(divideDecimalHalfUp('-0.001', '1', 2)).toBe('0.00');
    expect(formatScaledBigInt(-105n, 2)).toBe('-1.05');
    expect(formatScaledBigInt(0n, 2)).toBe('0.00');
    expect(scaleRoundedHalfUp({ negative: true, digits: 1005n, scale: 3 }, 2)).toBe(-101n);
  });
});
