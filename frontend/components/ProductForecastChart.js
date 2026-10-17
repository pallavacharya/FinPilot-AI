import { useState, useRef } from "react";

function formatK(val) {
  if (val === 0) return "$0";
  if (val >= 1000) {
    const k = val / 1000;
    return `$${k >= 10 ? Math.round(k) : k.toFixed(1)}K`;
  }
  return `$${Math.round(val)}`;
}

function formatCurrency(val) {
  return "$" + Number(val).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ProductForecastChart({ chartData, loading, error }) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const svgRef = useRef(null);

  if (loading) {
    return (
      <div style={{ height: 320, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted)" }}>
        <span>Loading forecast chart…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height: 320, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--red)" }}>
        <span>Couldn't load the forecast</span>
      </div>
    );
  }

  if (!chartData || !chartData.history || !chartData.forecast || chartData.history.length === 0) {
    return (
      <div style={{ height: 320, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted)" }}>
        <span>No forecast data available</span>
      </div>
    );
  }

  const { history, forecast } = chartData;
  const lastHistory = history[history.length - 1];

  // Combined list of points for positioning and hover
  // History: index 0 .. history.length - 1
  // Forecast: index history.length .. total - 1
  const allPoints = [
    ...history.map((h, i) => ({ ...h, isForecast: false, idx: i })),
    ...forecast.map((f, i) => ({ ...f, isForecast: true, idx: history.length + i })),
  ];

  const totalPoints = allPoints.length;

  // Layout constants
  const W = 760;
  const H = 320;
  const padLeft = 65;
  const padRight = 35;
  const padTop = 25;
  const padBottom = 40;
  const plotW = W - padLeft - padRight;
  const plotH = H - padTop - padBottom;

  // Determine Max Y value
  const allValues = [
    ...history.map((h) => h.sales),
    ...forecast.map((f) => f.upper || f.predicted),
  ];
  const rawMax = Math.max(...allValues, 100);
  // Round up to nice number
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)));
  const step = rawMax / magnitude > 5 ? magnitude : magnitude / 2;
  const maxY = Math.ceil((rawMax * 1.1) / step) * step;

  const getX = (idx) => padLeft + (idx / (totalPoints - 1)) * plotW;
  const getY = (val) => padTop + plotH - (Math.max(0, val) / maxY) * plotH;

  // History path
  const historyPath = history
    .map((h, i) => `${i === 0 ? "M" : "L"} ${getX(i).toFixed(1)} ${getY(h.sales).toFixed(1)}`)
    .join(" ");

  // Forecast path joined smoothly to the last history point
  const lastHistX = getX(history.length - 1);
  const lastHistY = getY(lastHistory.sales);

  const forecastPointsPath = forecast
    .map((f, i) => `L ${getX(history.length + i).toFixed(1)} ${getY(f.predicted).toFixed(1)}`)
    .join(" ");
  const forecastPath = `M ${lastHistX.toFixed(1)} ${lastHistY.toFixed(1)} ${forecastPointsPath}`;

  // Forecast uncertainty band
  const bandTop = forecast.map((f, i) => [getX(history.length + i), getY(f.upper)]);
  const bandBottom = forecast
    .map((f, i) => [getX(history.length + i), getY(f.lower)])
    .reverse();

  // Band smoothly starts at last history point
  const bandPath = [
    `M ${lastHistX.toFixed(1)} ${lastHistY.toFixed(1)}`,
    ...bandTop.map((p) => `L ${p[0].toFixed(1)} ${p[1].toFixed(1)}`),
    ...bandBottom.map((p) => `L ${p[0].toFixed(1)} ${p[1].toFixed(1)}`),
    `Z`,
  ].join(" ");

  // Y-axis gridlines (4-5 ticks)
  const numYTicks = 5;
  const yTicks = [];
  for (let i = 0; i <= numYTicks; i++) {
    const val = (maxY / numYTicks) * i;
    yTicks.push(val);
  }

  // X-axis month ticks: pick dates where month changes or key intervals
  const xTicks = [];
  let prevMonth = "";
  allPoints.forEach((pt, i) => {
    if (!pt.date) return;
    const dateObj = new Date(pt.date + "T00:00:00");
    const monthYear = dateObj.toLocaleDateString("en-US", { month: "short" });
    const fullYear = dateObj.getFullYear();
    // Only add tick if month changed and has spacing
    if (monthYear !== prevMonth) {
      if (xTicks.length === 0 || i - xTicks[xTicks.length - 1].idx >= 4) {
        const label = monthYear === "Jan" ? `Jan '${String(fullYear).slice(2)}` : monthYear;
        xTicks.push({ idx: i, label, x: getX(i) });
        prevMonth = monthYear;
      }
    }
  });

  const handlePointerMove = (e) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, (mouseX - (padLeft / W) * rect.width) / ((plotW / W) * rect.width)));
    const closestIdx = Math.round(ratio * (totalPoints - 1));
    if (closestIdx >= 0 && closestIdx < totalPoints) {
      setHoverIndex(closestIdx);
    }
  };

  const handlePointerLeave = () => {
    setHoverIndex(null);
  };

  const activePoint = hoverIndex !== null ? allPoints[hoverIndex] : null;
  const activeX = hoverIndex !== null ? getX(hoverIndex) : null;
  const activeY =
    activePoint !== null
      ? getY(activePoint.isForecast ? activePoint.predicted : activePoint.sales)
      : null;

  return (
    <div style={{ width: "100%", position: "relative" }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "auto", display: "block", userSelect: "none", cursor: "crosshair" }}
        onMouseMove={handlePointerMove}
        onMouseLeave={handlePointerLeave}
        onTouchMove={(e) => {
          if (e.touches[0]) handlePointerMove(e.touches[0]);
        }}
        onTouchEnd={handlePointerLeave}
      >
        <defs>
          <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3ECF8E" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#3ECF8E" stopOpacity="0.08" />
          </linearGradient>
        </defs>

        {/* Y Gridlines and Labels */}
        {yTicks.map((val, i) => {
          const y = getY(val);
          return (
            <g key={i}>
              <line
                x1={padLeft}
                y1={y}
                x2={W - padRight}
                y2={y}
                stroke="#2A3242"
                strokeWidth="1"
                strokeDasharray={val === 0 ? "none" : "3 3"}
              />
              <text
                x={padLeft - 10}
                y={y + 4}
                textAnchor="end"
                fill="var(--faint)"
                fontSize="11"
                fontFamily="var(--font-mono)"
              >
                {formatK(val)}
              </text>
            </g>
          );
        })}

        {/* X Axis Month Labels */}
        {xTicks.map((tick, i) => (
          <g key={i}>
            <line
              x1={tick.x}
              y1={padTop + plotH}
              x2={tick.x}
              y2={padTop + plotH + 5}
              stroke="#2A3242"
              strokeWidth="1"
            />
            <text
              x={tick.x}
              y={padTop + plotH + 20}
              textAnchor="middle"
              fill="var(--muted)"
              fontSize="11"
              fontFamily="var(--font-ui)"
            >
              {tick.label}
            </text>
          </g>
        ))}

        {/* Vertical Separator between History and Forecast */}
        <line
          x1={lastHistX}
          y1={padTop}
          x2={lastHistX}
          y2={padTop + plotH}
          stroke="#5D6578"
          strokeWidth="1"
          strokeDasharray="4 4"
        />

        {/* Forecast 80% Uncertainty Band */}
        <path d={bandPath} fill="url(#bandGradient)" />

        {/* 52 Weeks History Line */}
        <path d={historyPath} fill="none" stroke="#5D6578" strokeWidth="2" strokeLinecap="round" />

        {/* 4 Weeks Forecast Line */}
        <path d={forecastPath} fill="none" stroke="#3ECF8E" strokeWidth="2.5" strokeLinecap="round" />

        {/* Forecast Points Dots */}
        {forecast.map((f, i) => {
          const fx = getX(history.length + i);
          const fy = getY(f.predicted);
          return (
            <circle
              key={i}
              cx={fx}
              cy={fy}
              r="3.5"
              fill="#10141B"
              stroke="#3ECF8E"
              strokeWidth="2"
            />
          );
        })}

        {/* Interactive Hover Guide & Dots */}
        {activePoint && (
          <g>
            <line
              x1={activeX}
              y1={padTop}
              x2={activeX}
              y2={padTop + plotH}
              stroke="#E7EAF1"
              strokeWidth="1"
              strokeDasharray="2 2"
              opacity="0.7"
            />
            <circle
              cx={activeX}
              cy={activeY}
              r="5"
              fill={activePoint.isForecast ? "#3ECF8E" : "#E7EAF1"}
              stroke="#10141B"
              strokeWidth="2"
            />

            {/* Hover Tooltip Box */}
            {(() => {
              const isRightSide = activeX > W / 2;
              const boxW = activePoint.isForecast ? 165 : 135;
              const boxH = activePoint.isForecast ? 66 : 48;
              const boxX = isRightSide ? activeX - boxW - 12 : activeX + 12;
              const boxY = Math.max(padTop + 5, Math.min(padTop + plotH - boxH - 5, activeY - boxH / 2));

              return (
                <g>
                  <rect
                    x={boxX}
                    y={boxY}
                    width={boxW}
                    height={boxH}
                    rx="6"
                    fill="#171C26"
                    stroke="#2A3242"
                    strokeWidth="1"
                    filter="drop-shadow(0 4px 10px rgba(0,0,0,0.5))"
                  />
                  <text
                    x={boxX + 10}
                    y={boxY + 16}
                    fill="var(--muted)"
                    fontSize="10.5"
                    fontFamily="var(--font-mono)"
                  >
                    {activePoint.date} {activePoint.isForecast ? "(Forecast)" : ""}
                  </text>
                  <text
                    x={boxX + 10}
                    y={boxY + 34}
                    fill={activePoint.isForecast ? "#3ECF8E" : "#E7EAF1"}
                    fontSize="13"
                    fontWeight="600"
                    fontFamily="var(--font-mono)"
                  >
                    {activePoint.isForecast
                      ? `Est: ${formatCurrency(activePoint.predicted)}`
                      : `Sales: ${formatCurrency(activePoint.sales)}`}
                  </text>
                  {activePoint.isForecast && (
                    <text
                      x={boxX + 10}
                      y={boxY + 52}
                      fill="var(--faint)"
                      fontSize="10"
                      fontFamily="var(--font-mono)"
                    >
                      Range: {formatCurrency(activePoint.lower)} – {formatCurrency(activePoint.upper)}
                    </text>
                  )}
                </g>
              );
            })()}
          </g>
        )}
      </svg>

      {/* Legend below chart */}
      <div style={{ display: "flex", gap: 20, marginTop: 8, fontSize: 11.5, color: "var(--muted)", alignItems: "center" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <i style={{ width: 14, height: 2, background: "#5D6578", display: "inline-block" }}></i>
          52-week sales history
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <i style={{ width: 14, height: 2.5, background: "#3ECF8E", display: "inline-block" }}></i>
          4-week Prophet forecast
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <i style={{ width: 14, height: 10, background: "rgba(62,207,142,0.25)", border: "1px solid #3ECF8E", display: "inline-block", borderRadius: 2 }}></i>
          80% uncertainty interval
        </span>
      </div>
    </div>
  );
}
