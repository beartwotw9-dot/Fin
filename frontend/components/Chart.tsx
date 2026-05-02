"use client";
import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp
} from "lightweight-charts";
import type { Candle } from "@/lib/api";

interface Props {
  data: Candle[];
  height?: number;
}

/** 台股慣例：漲紅 (#f04060) / 跌綠 (#00c47a). */
export default function Chart({ data, height = 480 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  // init
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#161b27" },
        textColor: "#e8edf5",
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"
      },
      grid: {
        vertLines: { color: "#2a3350" },
        horzLines: { color: "#2a3350" }
      },
      timeScale: {
        borderColor: "#2a3350",
        timeVisible: true,
        secondsVisible: false
      },
      rightPriceScale: { borderColor: "#2a3350" },
      crosshair: { mode: 1 },
      autoSize: true,
      height
    });

    const candle = chart.addCandlestickSeries({
      upColor: "#f04060",
      downColor: "#00c47a",
      borderUpColor: "#f04060",
      borderDownColor: "#00c47a",
      wickUpColor: "#f04060",
      wickDownColor: "#00c47a"
    });

    const volume = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol"
    });
    chart.priceScale("vol").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 }
    });

    chartRef.current = chart;
    candleRef.current = candle;
    volRef.current = volume;

    const onResize = () => chart.applyOptions({ autoSize: true });
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // update on data change
  useEffect(() => {
    if (!candleRef.current || !volRef.current) return;

    const candles = data.map((d) => ({
      time: (Math.floor(new Date(d.date).getTime() / 1000) as UTCTimestamp),
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close
    }));
    const volumes = data.map((d) => ({
      time: (Math.floor(new Date(d.date).getTime() / 1000) as UTCTimestamp),
      value: d.volume,
      color: d.close >= d.open ? "rgba(240, 64, 96, 0.5)" : "rgba(0, 196, 122, 0.5)"
    }));

    candleRef.current.setData(candles);
    volRef.current.setData(volumes);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
