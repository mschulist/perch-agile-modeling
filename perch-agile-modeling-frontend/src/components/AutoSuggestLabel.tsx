import React, { useState } from "react"
import { Input } from "./ui/input"

const InputWithSuggestions = ({
    suggestions,
    customSpecies,
    setCustomSpecies,
}: {
    suggestions: string[]
    customSpecies: string
    setCustomSpecies: (species: string) => void
}) => {
    const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([])

    console.log(customSpecies)

    const handleChange = (e: any) => {
        const value = e.target.value
        setCustomSpecies(value)

        if (value) {
            const filtered = suggestions.filter((suggestion) =>
                suggestion.toLowerCase().startsWith(value.toLowerCase())
            )
            setFilteredSuggestions(filtered.slice(0, 3)) // limit to 3 suggestions
        } else {
            setFilteredSuggestions([])
        }
    }

    const handleSuggestionClick = (suggestion: string) => {
        setCustomSpecies(suggestion)
        setFilteredSuggestions([])
    }

    return (
        <div className="relative">
            <Input
                type="text"
                value={customSpecies}
                onChange={handleChange}
                className="w-full ml-2 p-1 transition duration-100 text-center"
                placeholder="species_type"
            />
            {filteredSuggestions.length > 0 && (
                <ul className="absolute left-0 right-0 mt-1 bg-black rounded shadow-lg transition duration-300 list-none">
                    {filteredSuggestions.map((suggestion, index) => (
                        <li
                            key={index}
                            onClick={() => handleSuggestionClick(suggestion)}
                            className="px-4 py-2 cursor-pointer hover:bg-gray-800 transition duration-100 text-center"
                        >
                            {suggestion}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}

export default InputWithSuggestions
