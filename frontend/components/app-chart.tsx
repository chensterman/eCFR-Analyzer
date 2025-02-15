"use client"

import * as React from "react"
import { Line, LineChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type DataPoint = {
  date: string;
  [key: string]: string | number;
};

type ChartProps = {
  metricName: string;
  queryBy: string;
  data: DataPoint[];
}

type ChartConfigItem = {
  label: string;
  color: string;
};

type DynamicChartConfig = {
  [key: string]: ChartConfigItem;
};

const timeRangeOptions = {
  "1y": { label: "1 Year", years: 1 },
  "5y": { label: "5 Years", years: 5 },
  "all": { label: "All Time", years: Infinity }
} as const;

const colors = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
]

export function Chart({ metricName, queryBy, data }: ChartProps) {
  const [timeRange, setTimeRange] = React.useState<keyof typeof timeRangeOptions>("1y")

  const filterDataByTimeRange = (data: DataPoint[], range: keyof typeof timeRangeOptions) => {
    const cutoffDate = new Date();
    if (range !== 'all') {
      cutoffDate.setFullYear(cutoffDate.getFullYear() - timeRangeOptions[range].years);
    } else {
      cutoffDate.setFullYear(2017, 0, 1); // Jan 1, 2017
    }
    return data.filter(item => new Date(item.date) >= cutoffDate);
  };

  // Generate chart config based on data
  const getChartConfig = (): DynamicChartConfig => {
    if (!data.length) return {};
    
    const keys = Object.keys(data[0]).filter(key => key !== 'date');
    return keys.reduce((config, key, index) => ({
      ...config,
      [key]: {
        label: key,
        color: colors[index],
      }
    }), {} as DynamicChartConfig);
  };

  const chartConfig = getChartConfig();
  console.log(chartConfig);

  const filteredData = filterDataByTimeRange(data, timeRange);

  return (
    <Card className="w-full h-full p-2">
      <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-row">
        <div className="grid flex-1 gap-1 text-center sm:text-left">
          <CardTitle>eCFR Analyzer</CardTitle>
          <CardDescription>
            {data.length > 0 
              ? `Showing ${metricName.replace('-', ' ')} by ${queryBy} for ${timeRangeOptions[timeRange].label.toLowerCase()}`
              : "Select options to visualize data"
            }
          </CardDescription>
        </div>
        <Select 
          value={timeRange} 
          onValueChange={(value) => setTimeRange(value as keyof typeof timeRangeOptions)}
        >
          <SelectTrigger
            className="w-[160px] rounded-lg sm:ml-auto"
            aria-label="Select time range"
          >
            <SelectValue placeholder="Select time range" />
          </SelectTrigger>
          <SelectContent className="rounded-xl">
            {Object.entries(timeRangeOptions).map(([value, { label }]) => (
              <SelectItem key={value} value={value} className="rounded-lg">
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent className="flex-1 px-2 pt-4 sm:px-6 sm:pt-6 flex flex-col h-[calc(100vh-120px)]">
        <ChartContainer
          config={chartConfig}
          className="flex-1 w-full h-full"
        >
          <LineChart data={filteredData} className="w-full h-full">
            <defs>
              {Object.entries(chartConfig).map(([key, config]: [string, ChartConfigItem]) => (
                <linearGradient key={key} id={`fill${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={config.color}
                    stopOpacity={0.8}
                  />
                  <stop
                    offset="95%"
                    stopColor={config.color}
                    stopOpacity={0.1}
                  />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`;
              }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(value) => value.toLocaleString()}
              label={{ 
                value: metricName.replace('-', ' '), 
                angle: -90,
                position: 'insideLeft',
                style: { 
                  textAnchor: 'middle',
                  fill: 'var(--foreground)',
                  fontSize: '0.8rem'
                }
              }}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelFormatter={(value) => {
                    const date = new Date(value);
                    return `${String(date.getMonth() + 1).padStart(2, '0')}-${date.getFullYear()}`;
                  }}
                  indicator="dot"
                />
              }
            />
            {Object.keys(chartConfig).map((key) => (
              <Line
                key={key}
                dataKey={key}
                type="monotone"
                stroke={chartConfig[key].color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2 }}
              />
            ))}
            <ChartLegend content={<ChartLegendContent />} />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
