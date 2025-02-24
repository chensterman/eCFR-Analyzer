import agenciesData from '@/public/agencies.json'

// Constants containing agency JSON data
export const agencies = [...agenciesData.agencies].sort((a, b) => a.name.localeCompare(b.name));

interface DataPoint {
  date: string;
  [key: string]: string | number | null;
}

export const supabaseHandler = async (
  queryBy: string,
  selectedItems: string[],
  selectedMetric: string,
): Promise<DataPoint[]> => {
  try {
    const response = await fetch('/api/supabase', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        queryBy,
        selectedItems,
        selectedMetric,
      }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching data:', error);
    return [];
  }
};