'use client'

import { Chart } from "@/components/app-chart"
import { SidebarProvider } from "@/components/ui/sidebar"
import Image from "next/image"
import { useState } from 'react'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
} from "@/components/ui/sidebar"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { MultiSelect } from "@/components/app-multi-select"
import { supabaseHandler } from '@/lib/supabase'
import agenciesData from '@/public/agencies.json'
import titlesData from '@/public/titles.json'

type SidebarState = {
  queryBy: string;
  selectedAgencies: string[];
  selectedTitles: string[];
  selectedMetric: string;
}

type DataPoint = {
  date: string;
  [key: string]: string | number | null;
};

type ChartState = {
  queryBy: string;
  metricName: string;
  data: DataPoint[];
}

// Constants containing agency and title JSON data
const agencies = [...agenciesData.agencies].sort((a, b) => a.name.localeCompare(b.name));
const titles = titlesData.titles;

export default function Home() {
  // Initialize states
  const [sidebarState, setSidebarState] = useState<SidebarState>({
    queryBy: 'agency',
    selectedAgencies: [],
    selectedTitles: [],
    selectedMetric: ''
  });
  const [chartState, setChartState] = useState<ChartState>({
    queryBy: '',
    metricName: '',
    data: []
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Function to fetch data from Supabase client
  const fetchData = async () => {
    if (!sidebarState.queryBy || !sidebarState.selectedMetric) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const mockData = await supabaseHandler(
        sidebarState.queryBy,
        sidebarState.queryBy === 'cfr-title' ? sidebarState.selectedTitles : sidebarState.selectedAgencies,
        sidebarState.selectedMetric
      );

      console.log(mockData);

      setChartState({
        queryBy: sidebarState.queryBy,
        metricName: sidebarState.selectedMetric,
        data: mockData
      });
    } catch (err) {
      console.error('Error generating mock data:', err);
      setError('Failed to generate data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch data when the visualize button is clicked
  const handleVisualize = () => {
    fetchData();
  };

  return (
    <div className="flex items-center justify-center">
      <SidebarProvider>
        <Sidebar>
          <SidebarHeader>
            <div className="p-2 flex items-center gap-3">
              <Image 
                src="/DOGE.jpg" 
                alt="DOGE" 
                width={40} 
                height={40} 
                className="rounded-full"
              />
              <span className="font-semibold text-4xl">DOGE</span>
            </div>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Query By</SidebarGroupLabel>
              <SidebarGroupContent>
                <Select 
                  defaultValue="agency"
                  onValueChange={(value) => {
                    setSidebarState(prev => ({ 
                      ...prev, 
                      queryBy: value,
                      // Reset selections when switching query type
                      selectedAgencies: [],
                      selectedTitles: []
                    }))
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="agency">Agency</SelectItem>
                    <SelectItem value="cfr-title">CFR Title</SelectItem>
                  </SelectContent>
                </Select>
              </SidebarGroupContent>
            </SidebarGroup>
            {sidebarState.queryBy === 'agency' && (
              <SidebarGroup>
                <SidebarGroupLabel>Select Agencies (max 3)</SidebarGroupLabel>
                <SidebarGroupContent>
                  <MultiSelect 
                    onChange={(values) => setSidebarState(prev => ({ ...prev, selectedAgencies: values }))}
                    options={agencies.map(agency => ({
                      value: agency.name,
                      label: agency.name
                    }))}
                    placeholder="Select Agencies"
                    maxSelections={3}
                  />
                </SidebarGroupContent>
              </SidebarGroup>
            )}
            {sidebarState.queryBy === 'cfr-title' && (
              <SidebarGroup>
                <SidebarGroupLabel>Select Titles (max 3)</SidebarGroupLabel>
                <SidebarGroupContent>
                  <MultiSelect 
                    onChange={(values) => setSidebarState(prev => ({ ...prev, selectedTitles: values }))}
                    options={titles.map(title => ({
                      value: title.id,
                      label: title.name
                    }))}
                    placeholder="Select Titles"
                    maxSelections={3}
                  />
                </SidebarGroupContent>
              </SidebarGroup>
            )}
            <SidebarGroup>
              <SidebarGroupLabel>Select Metric</SidebarGroupLabel>
              <SidebarGroupContent>
                <Select onValueChange={(value) => setSidebarState(prev => ({ ...prev, selectedMetric: value }))}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="word_count">Word Count</SelectItem>
                    <SelectItem value="mandate_count">Mandate Count</SelectItem>
                    <SelectItem value="readability_score">Readability Score</SelectItem>
                  </SelectContent>
                </Select>
              </SidebarGroupContent>
            </SidebarGroup>
            {sidebarState.selectedMetric && (
              <SidebarGroup>
                <SidebarGroupContent>
                  <div className="text-xs text-muted-foreground space-y-2">
                    {sidebarState.selectedMetric === 'word_count' && (
                      <>
                        <p>Word count is a basic measure of regulatory complexity. Higher word counts often indicate more complex and detailed regulations, which can impact government efficiency by:</p>
                        <ul className="list-disc pl-4 space-y-1">
                          <li>Increasing compliance costs</li>
                          <li>Making regulations harder to understand</li>
                          <li>Requiring more time to review and implement</li>
                        </ul>
                      </>
                    )}
                    {sidebarState.selectedMetric === 'mandate_count' && (
                      <>
                        <p>Mandate count measures the frequency of restrictive words like &ldquo;shall,&rdquo; &ldquo;must,&rdquo; &ldquo;require,&rdquo; and &ldquo;prohibited.&rdquo; This metric indicates the level of regulatory burden by counting explicit requirements and restrictions.</p>
                        <p className="mt-2">A higher mandate count suggests:</p>
                        <ul className="list-disc pl-4 space-y-1">
                          <li>More prescriptive regulations</li>
                          <li>Less flexibility in implementation</li>
                          <li>Increased compliance requirements</li>
                        </ul>
                      </>
                    )}
                    {sidebarState.selectedMetric === 'readability_score' && (
                      <>
                        <p>The Flesch-Kincaid readability score measures how easy it is to understand the text. The score ranges from 0-100, with 0 being extremely difficult to read, and 100 being very easy to read. You can read more about this{" "}
                          <a 
                            href="https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            here
                          </a>.
                        </p>
                        <p className="mt-2">Lower readability scores can impact government efficiency by:</p>
                        <ul className="list-disc pl-4 space-y-1">
                          <li>Making regulations harder to understand and follow</li>
                          <li>Increasing the need for legal interpretation</li>
                          <li>Reducing public compliance due to confusion</li>
                        </ul>
                      </>
                    )}
                  </div>
                </SidebarGroupContent>
              </SidebarGroup>
            )}
            <SidebarGroup>
              <SidebarGroupContent>
                <Button 
                  className="w-full" 
                  onClick={handleVisualize}
                  disabled={isLoading || !sidebarState.queryBy || !sidebarState.selectedMetric || 
                    (sidebarState.queryBy === 'agency' && sidebarState.selectedAgencies.length === 0) ||
                    (sidebarState.queryBy === 'cfr-title' && sidebarState.selectedTitles.length === 0)}
                >
                  {isLoading ? "Loading..." : "Visualize"}
                </Button>
                {error && (
                  <p className="text-xs text-destructive mt-2">{error}</p>
                )}
              </SidebarGroupContent>
            </SidebarGroup>
            <SidebarGroup>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>
      </SidebarProvider>
      <Chart 
        metricName={sidebarState.selectedMetric}
        queryBy={sidebarState.queryBy}
        data={chartState.data}
      />
    </div>
  );
}
