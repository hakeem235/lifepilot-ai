/**
 * Lightweight SVG charts for Insights: a bar chart (tasks/day) and a filled area
 * chart (focus minutes/day). No chart library — just react-native-svg primitives,
 * so the bundle stays lean and styling matches our tokens.
 */
import { View } from "react-native";
import Svg, { Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { brand } from "../../theme/tokens";

const W = 300;
const H = 120;
const PAD = 8;

export function BarChart({ data }: { data: number[] }) {
  const max = Math.max(1, ...data);
  const n = data.length || 1;
  const bw = (W - PAD * 2) / n;
  return (
    <View>
      <Svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
        {data.map((v, i) => {
          const h = (v / max) * (H - PAD * 2);
          return (
            <Rect
              key={i}
              x={PAD + i * bw + bw * 0.2}
              y={H - PAD - h}
              width={bw * 0.6}
              height={Math.max(2, h)}
              rx={4}
              fill={brand.primary}
              opacity={0.85}
            />
          );
        })}
      </Svg>
    </View>
  );
}

export function AreaChart({ data }: { data: number[] }) {
  const max = Math.max(1, ...data);
  const n = data.length;
  if (n < 2) return <View style={{ height: H }} />;
  const x = (i: number) => PAD + (i / (n - 1)) * (W - PAD * 2);
  const y = (v: number) => H - PAD - (v / max) * (H - PAD * 2);
  const line = data.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(v)}`).join(" ");
  const area = `${line} L ${x(n - 1)} ${H - PAD} L ${x(0)} ${H - PAD} Z`;
  return (
    <View>
      <Svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
        <Defs>
          <LinearGradient id="focusFill" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={brand.accent} stopOpacity="0.5" />
            <Stop offset="1" stopColor={brand.accent} stopOpacity="0.05" />
          </LinearGradient>
        </Defs>
        <Path d={area} fill="url(#focusFill)" />
        <Path d={line} stroke={brand.accent} strokeWidth={2.5} fill="none" strokeLinejoin="round" />
      </Svg>
    </View>
  );
}
