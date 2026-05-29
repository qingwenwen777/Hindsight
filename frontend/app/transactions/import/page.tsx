"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PreviewRow {
  symbol: string;
  market: string;
  type: string;
  trade_date: string;
  quantity: string;
  price: string;
  currency: string;
  error: string | null;
}

interface PreviewData {
  broker: string;
  columns: string[];
  total: number;
  valid: number;
  invalid: number;
  rows: PreviewRow[];
}

/**
 * CSV 导入页（设计文档 8.7 / FE-4.5）。
 * 上传 → 自动检测格式 → 预览（有效/无效行）→ 批量提交。
 */
export default function ImportPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const doPreview = async (f: File) => {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const resp = await fetch(`${API_BASE}/api/v1/transactions/import/preview`, {
        method: "POST",
        body: fd,
      });
      const body = await resp.json();
      if (body.code !== 0) throw new Error(body.message);
      setPreview(body.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "预览失败");
    } finally {
      setLoading(false);
    }
  };

  const doImport = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch(`${API_BASE}/api/v1/transactions/import`, {
        method: "POST",
        body: fd,
      });
      const body = await resp.json();
      if (body.code !== 0) throw new Error(body.message);
      setResult(`导入完成：写入 ${body.data.inserted} 笔，跳过 ${body.data.skipped} 笔`);
      setPreview(null);
      setFile(null);
      qc.invalidateQueries({ queryKey: ["holdings"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "导入失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-h1 text-primary">批量导入</h1>
        <p className="text-small text-secondary">
          上传券商 CSV（富途 / 雪球 / 通用格式），自动检测并预览后批量写入。导入项会创建占位日志，可后期补写。
        </p>
      </div>

      <Card>
        <CardContent className="flex items-center gap-4 p-4">
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                setFile(f);
                doPreview(f);
              }
            }}
          />
          <Button onClick={() => fileRef.current?.click()} disabled={loading}>
            选择 CSV 文件
          </Button>
          {file && <span className="text-small text-secondary">{file.name}</span>}
        </CardContent>
      </Card>

      {error && <p className="text-small text-danger">{error}</p>}
      {result && <p className="text-small text-up">{result}</p>}

      {preview && (
        <Card>
          <CardHeader>
            <CardTitle>
              预览 · 检测格式 <span className="text-accent">{preview.broker}</span> · 共 {preview.total} 行（
              <span className="text-up">{preview.valid} 有效</span> /
              <span className="text-down"> {preview.invalid} 无效</span>）
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-small">
                <thead>
                  <tr className="border-b border-border-subtle text-caption text-secondary">
                    <th className="px-2 py-2 text-left">代码</th>
                    <th className="px-2 py-2 text-left">市场</th>
                    <th className="px-2 py-2 text-left">方向</th>
                    <th className="px-2 py-2 text-left">日期</th>
                    <th className="px-2 py-2 text-right">数量</th>
                    <th className="px-2 py-2 text-right">价格</th>
                    <th className="px-2 py-2 text-left">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((r, i) => (
                    <tr key={i} className="border-b border-border-subtle/50">
                      <td className="tnum px-2 py-2 text-primary">{r.symbol}</td>
                      <td className="px-2 py-2 text-secondary">{r.market}</td>
                      <td className="px-2 py-2">
                        <span className={r.type === "BUY" ? "text-up" : "text-down"}>{r.type}</span>
                      </td>
                      <td className="tnum px-2 py-2 text-secondary">{r.trade_date}</td>
                      <td className="tnum px-2 py-2 text-right text-primary">{r.quantity}</td>
                      <td className="tnum px-2 py-2 text-right text-primary">{r.price}</td>
                      <td className="px-2 py-2">
                        {r.error ? (
                          <span className="text-down">{r.error}</span>
                        ) : (
                          <span className="text-up">✓</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex justify-end">
              <Button onClick={doImport} disabled={loading || preview.valid === 0}>
                确认导入 {preview.valid} 笔
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
