"use client"

import * as React from "react"
import { Check } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface SelectOption {
  value: string;
  label: string;
}

interface MultiSelectProps {
  onChange?: (values: string[]) => void;
  options: SelectOption[];
  placeholder?: string;
  maxSelections?: number;
}

export function MultiSelect({ 
  onChange, 
  options, 
  placeholder = "Select Multiple",
  maxSelections = 3 
}: MultiSelectProps) {
  const [selectedOptions, setSelectedOptions] = React.useState<string[]>([])

  const handleSelectChange = (value: string) => {
    const isSelected = selectedOptions.includes(value);
    
    if (!isSelected && selectedOptions.length >= maxSelections) {
      // Don't add if we've reached the limit
      return;
    }

    const newValues = isSelected
      ? selectedOptions.filter((item) => item !== value) 
      : [...selectedOptions, value];
    
    setSelectedOptions(newValues);
    onChange?.(newValues);
  }

  return (
    <div className="relative w-full">
      <Select value={selectedOptions.join(",")}>
        <SelectTrigger className="w-full h-auto min-h-[40px] flex-wrap">
          <SelectValue placeholder={placeholder}>
            {selectedOptions.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {selectedOptions.map((option) => (
                  <span
                    key={option}
                    className="border bg-secondary text-secondary-foreground h-6 px-2 text-xs rounded flex items-center gap-1"
                  >
                    {options.find((opt) => opt.value === option)?.label}
                  </span>
                ))}
              </div>
            ) : (
              placeholder
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {options.map((option) => (
              <div
                key={option.value}
                className={`flex items-center justify-between px-2 py-1.5 cursor-pointer hover:bg-secondary ${
                  !selectedOptions.includes(option.value) && selectedOptions.length >= maxSelections ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                onClick={() => {
                  if (!selectedOptions.includes(option.value) && selectedOptions.length >= maxSelections) {
                    return;
                  }
                  handleSelectChange(option.value);
                }}
              >
                <span>{option.label}</span>
                {selectedOptions.includes(option.value) && <Check className="h-4 w-4 text-primary" />}
              </div>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  )
}
