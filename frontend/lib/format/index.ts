/**
 * 统一格式化函数（设计文档 8.1：等宽数字、tabular-nums）。
 * 金额/百分比/日期都走这里，保证全站一致。
 */

/** 货币符号映射 */
const CURRENCY_SYMBOL: Record<string, string> = {
  JPY: "¥",
  CNY: "¥",
  USD: "$",
  HKD: "HK$",
};

/**
 * 格式化金额。amount 接受字符串（后端 Decimal 字符串）或 number。
 * JPY 默认 0 位小数，其余 2 位。
 */
export function formatMoney(
  amount: string | number | null | undefined,
  currency = "JPY",
  opts: { sign?: boolean } = {},
): string {
  if (amount === null || amount === undefined || amount === "") return "—";
  const n = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(n)) return "—";
  const fractionDigits = currency === "JPY" ? 0 : 2;
  const sym = CURRENCY_SYMBOL[currency] ?? "";
  const body = Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
  const sign = n < 0 ? "-" : opts.sign ? "+" : "";
  return `${sign}${sym}${body}`;
}

/** 格式化百分比。输入为百分比数值（如 18.3 表示 18.3%）。 */
export function formatPercent(
  value: string | number | null | undefined,
  opts: { sign?: boolean; digits?: number } = {},
): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "—";
  const digits = opts.digits ?? 2;
  const sign = n > 0 && opts.sign ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

/** 格式化数量（股数），最多 4 位小数，去掉多余 0。 */
export function formatQuantity(qty: string | number | null | undefined): string {
  if (qty === null || qty === undefined || qty === "") return "—";
  const n = typeof qty === "string" ? Number(qty) : qty;
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

/** 判断涨跌方向：>0 up，<0 down，=0 flat。 */
export function pnlDirection(value: string | number | null | undefined): "up" | "down" | "flat" {
  if (value === null || value === undefined || value === "") return "flat";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n) || n === 0) return "flat";
  return n > 0 ? "up" : "down";
}

/** 格式化日期为 YYYY-MM-DD。 */
export function formatDate(d: string | Date | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  if (Number.isNaN(date.getTime())) return "—";
  return date.toISOString().slice(0, 10);
}
