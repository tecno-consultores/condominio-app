/**
 * Aritmética decimal determinista basada en BigInt con redondeo financiero ROUND_HALF_UP.
 * Evita errores de precisión binaria IEEE-754 (e.g. (1.005).toFixed(2) === "1.00").
 */

const DECIMAL_INPUT_REGEX = /^([+-])?(\d+)(?:\.(\d+))?$/;
const POW10_CACHE = new Map<number, bigint>();

function pow10(exp: number): bigint {
  let cached = POW10_CACHE.get(exp);
  if (cached === undefined) {
    cached = 10n ** BigInt(exp);
    POW10_CACHE.set(exp, cached);
  }
  return cached;
}

export interface ParsedDecimal {
  negative: boolean;
  digits: bigint;
  scale: number;
}

export function parseDecimal(value: string | number | null | undefined): ParsedDecimal | null {
  if (value === null || value === undefined) {
    return null;
  }
  const raw = (typeof value === 'number' ? String(value) : value).trim();
  if (!raw || (typeof value === 'number' && !Number.isFinite(value))) {
    return null;
  }
  const match = DECIMAL_INPUT_REGEX.exec(raw);
  if (!match) {
    return null;
  }
  const negative = match[1] === '-';
  const intPart = match[2];
  const fracPart = match[3] ?? '';
  const digits = BigInt(`${intPart}${fracPart}`);
  return {
    negative: negative && digits > 0n,
    digits,
    scale: fracPart.length,
  };
}

function divideAbsRoundHalfUp(numerator: bigint, denominator: bigint): bigint {
  const quotient = numerator / denominator;
  const remainder = numerator % denominator;
  if (remainder * 2n >= denominator) {
    return quotient + 1n;
  }
  return quotient;
}

export function formatScaledBigInt(value: bigint, decimals: number): string {
  const isNeg = value < 0n;
  const abs = isNeg ? -value : value;
  const factor = pow10(decimals);
  const intPart = abs / factor;
  const fracPart = abs % factor;
  const body =
    decimals > 0 ? `${intPart}.${fracPart.toString().padStart(decimals, '0')}` : `${intPart}`;
  return isNeg && abs > 0n ? `-${body}` : body;
}

export function scaleRoundedHalfUp(parsed: ParsedDecimal, decimals: number): bigint {
  let absScaled: bigint;
  if (parsed.scale <= decimals) {
    absScaled = parsed.digits * pow10(decimals - parsed.scale);
  } else {
    absScaled = divideAbsRoundHalfUp(parsed.digits, pow10(parsed.scale - decimals));
  }
  return parsed.negative && absScaled > 0n ? -absScaled : absScaled;
}

export function roundDecimalHalfUp(
  value: string | number | null | undefined,
  decimals = 2,
): string {
  const parsed = parseDecimal(value);
  if (!parsed) {
    return formatScaledBigInt(0n, decimals);
  }
  return formatScaledBigInt(scaleRoundedHalfUp(parsed, decimals), decimals);
}

export function multiplyDecimalHalfUp(
  a: string | number | null | undefined,
  b: string | number | null | undefined,
  decimals = 2,
): string {
  const pa = parseDecimal(a);
  const pb = parseDecimal(b);
  if (!pa || !pb) {
    return formatScaledBigInt(0n, decimals);
  }
  const rawProduct = pa.digits * pb.digits;
  const rawScale = pa.scale + pb.scale;
  const neg = pa.negative !== pb.negative;
  const scaled = scaleRoundedHalfUp(
    { negative: neg, digits: rawProduct, scale: rawScale },
    decimals,
  );
  return formatScaledBigInt(scaled, decimals);
}

export function divideDecimalHalfUp(
  numerator: string | number | null | undefined,
  denominator: string | number | null | undefined,
  decimals = 2,
): string {
  const pn = parseDecimal(numerator);
  const pd = parseDecimal(denominator);
  if (!pn || !pd || pd.digits === 0n) {
    return formatScaledBigInt(0n, decimals);
  }
  const scaledNum = pn.digits * pow10(pd.scale + decimals);
  const scaledDen = pd.digits * pow10(pn.scale);
  const absResult = divideAbsRoundHalfUp(scaledNum, scaledDen);
  const neg = pn.negative !== pd.negative;
  const signed = neg && absResult > 0n ? -absResult : absResult;
  return formatScaledBigInt(signed, decimals);
}

export function compareDecimal(
  a: string | number | null | undefined,
  b: string | number | null | undefined,
): -1 | 0 | 1 {
  const pa = parseDecimal(a);
  const pb = parseDecimal(b);
  if (!pa || !pb) {
    return 0;
  }
  const maxScale = Math.max(pa.scale, pb.scale);
  const va = pa.digits * pow10(maxScale - pa.scale) * (pa.negative ? -1n : 1n);
  const vb = pb.digits * pow10(maxScale - pb.scale) * (pb.negative ? -1n : 1n);
  if (va < vb) return -1;
  if (va > vb) return 1;
  return 0;
}

export function addDecimalHalfUp(
  values: Array<string | number | null | undefined>,
  decimals = 2,
): string {
  const parsedList = values
    .map((v) => parseDecimal(v))
    .filter((p): p is ParsedDecimal => p !== null);
  if (parsedList.length === 0) {
    return formatScaledBigInt(0n, decimals);
  }
  const commonScale = parsedList.reduce((acc, p) => Math.max(acc, p.scale, decimals), decimals);
  let sum = 0n;
  for (const item of parsedList) {
    const scaled = item.digits * pow10(commonScale - item.scale);
    sum += item.negative ? -scaled : scaled;
  }
  const neg = sum < 0n;
  const absSum = neg ? -sum : sum;
  const finalScaled = scaleRoundedHalfUp(
    { negative: neg, digits: absSum, scale: commonScale },
    decimals,
  );
  return formatScaledBigInt(finalScaled, decimals);
}
