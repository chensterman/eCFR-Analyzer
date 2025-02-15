"use client"

import * as React from "react"
import { Check } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
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

  const handleRemove = (value: string, e: React.MouseEvent) => {
    e.preventDefault();
    const newValues = selectedOptions.filter((item) => item !== value);
    setSelectedOptions(newValues);
    onChange?.(newValues);
  }

  return (
    <Select onValueChange={handleSelectChange} value={selectedOptions.join(",")}>
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
            <SelectItem 
              key={option.value} 
              value={option.value} 
              className="flex items-center justify-between"
              disabled={!selectedOptions.includes(option.value) && selectedOptions.length >= maxSelections}
            >
              <span>{option.label}</span>
              {selectedOptions.includes(option.value) && <Check className="h-4 w-4 text-primary" />}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}
