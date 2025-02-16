import { createClient } from '@supabase/supabase-js'
import agenciesData from '@/public/agencies.json'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const supabaseClient = createClient(supabaseUrl, supabaseAnonKey)

// Constants containing agency JSON data
export const agencies = [...agenciesData.agencies].sort((a, b) => a.name.localeCompare(b.name));

interface DataPoint {
  date: string;
  [key: string]: string | number | null;
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const supabaseHandler = async (
  queryBy: string,
  selectedItems: string[],
  selectedMetric: string,
): Promise<DataPoint[]> => {
    if (queryBy === 'agency') {
        // Get metrics for each agency separately
        const agencyResults = [];
        for (const agencyName of selectedItems) {
            const agency = agencies.find(a => a.name === agencyName);
            if (!agency?.cfr_references?.length) {
                agencyResults.push([]);
                continue;
            }

            // Get metrics for each title/chapter pair of this agency
            const pairResults = [];
            const validRefs = agency.cfr_references.filter(ref => ref.chapter !== undefined);
            
            for (const ref of validRefs) {
                const result = await getMetricTotalForPairs(
                    [ref.title.toString()], 
                    [ref.chapter], 
                    selectedMetric
                );
                pairResults.push(result);
                await delay(500); // Wait 500ms between requests
            }
            
            // Combine all pairs for this agency
            const agencyDataByDate = new Map<string, { total: number, count: number }>();
            
            pairResults.forEach(pairData => {
                pairData.forEach(dataPoint => {
                    const date = dataPoint.date;
                    const value = Object.values(dataPoint).find(v => typeof v === 'number') as number || 0;
                    
                    if (!agencyDataByDate.has(date)) {
                        agencyDataByDate.set(date, { total: 0, count: 0 });
                    }
                    
                    const current = agencyDataByDate.get(date)!;
                    current.total += value;
                    current.count += 1;
                });
            });
            
            agencyResults.push(Array.from(agencyDataByDate.entries()).map(([date, { total, count }]) => ({
                date,
                [agencyName]: selectedMetric === 'readability_score' 
                    ? count > 0 ? total / count : null  // Average for readability
                    : total                             // Sum for other metrics
            })));

            await delay(1000); // Wait 1 second between agencies
        }
        
        // Combine all agency data
        const finalDataByDate = new Map<string, DataPoint>();
        
        // First, create entries for all dates with null values for all agencies
        const allDates = new Set<string>();
        agencyResults.forEach(agencyData => {
            agencyData.forEach(dataPoint => allDates.add(dataPoint.date));
        });
        
        allDates.forEach(date => {
            const dataPoint: DataPoint = { date };
            selectedItems.forEach(agency => {
                dataPoint[agency] = null;
            });
            finalDataByDate.set(date, dataPoint);
        });
        
        // Then fill in the actual values
        agencyResults.forEach(agencyData => {
            agencyData.forEach(dataPoint => {
                Object.entries(dataPoint).forEach(([key, value]) => {
                    if (key !== 'date') {
                        finalDataByDate.get(dataPoint.date)![key] = value;
                    }
                });
            });
        });

        return Array.from(finalDataByDate.values()).sort((a, b) => 
            a.date.localeCompare(b.date)
        );
    }
    if (queryBy === 'cfr-title') {
        // Get metrics for each title sequentially
        const titleResults = [];
        for (const title of selectedItems) {
            const result = await getMetricTotalForTitle(title, selectedMetric);
            titleResults.push(result);
            await delay(1000); // Wait 1 second between titles
        }
        
        // First, collect all unique dates
        const allDates = new Set<string>();
        titleResults.forEach(titleData => {
            titleData.forEach(dataPoint => allDates.add(dataPoint.date));
        });
        
        // Create map with all dates and initialize with null values for all titles
        const finalDataByDate = new Map<string, DataPoint>();
        allDates.forEach(date => {
            const dataPoint: DataPoint = { date };
            selectedItems.forEach(title => {
                dataPoint[title] = null;
            });
            finalDataByDate.set(date, dataPoint);
        });
        
        // Fill in actual values where they exist
        titleResults.forEach((titleData, index) => {
            const title = selectedItems[index];
            titleData.forEach(dataPoint => {
                const value = Object.values(dataPoint).find(v => typeof v === 'number') as number || null;
                finalDataByDate.get(dataPoint.date)![title] = value;
            });
        });

        return Array.from(finalDataByDate.values()).sort((a, b) => 
            a.date.localeCompare(b.date)
        );
    }
    return [];
};

interface YearMetric {
    target_date: string; // ISO date string
    total_metric: number;
  }
  
export async function getMetricTotalForPairs(
    titles: string[],
    chapters: string[],
    metric: string     // e.g., 'word_count', 'readability_score', or 'mandate_count'
): Promise<DataPoint[]> {
    const { data, error } = await supabaseClient.rpc('get_metric_total_for_pairs', {
        title_list: titles,
        chapter_list: chapters,
        metric: metric,
    });

    if (error) {
        console.error('Error fetching metric totals:', error);
        return [];
    }

    // Transform the data into DataPoint format
    const dataByDate = new Map<string, DataPoint>();
    
    (data as YearMetric[]).forEach((row) => {
        const date = row.target_date;
        const key = `${titles[0]}-${chapters[0]}`; // Assuming pairs are matched in order
        
        if (!dataByDate.has(date)) {
            dataByDate.set(date, { date });
        }
        
        const dataPoint = dataByDate.get(date)!;
        dataPoint[key] = row.total_metric;
    });

    return Array.from(dataByDate.values()).sort((a, b) => 
        a.date.localeCompare(b.date)
    );
}

export async function getMetricTotalForTitle(
    title: string,
    metric: string // e.g., 'word_count', 'readability_score', or 'mandate_count'
): Promise<DataPoint[]> {
    const { data, error } = await supabaseClient.rpc('get_metric_total_for_title', {
        title_param: title,
        metric: metric,
    });

    if (error) {
        console.error('Error fetching metric totals:', error);
        return [];
    }

    // Transform the data into DataPoint format
    const dataByDate = new Map<string, DataPoint>();
    
    (data as YearMetric[]).forEach((row) => {
        const date = row.target_date;
        
        if (!dataByDate.has(date)) {
            dataByDate.set(date, { date });
        }
        
        const dataPoint = dataByDate.get(date)!;
        dataPoint[title] = row.total_metric;
    });

    return Array.from(dataByDate.values()).sort((a, b) => 
        a.date.localeCompare(b.date)
    );
}