import React, { useRef, useState } from "react"
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
    const suggestionsContainerRef = useRef<HTMLUListElement | null>(null)
    const [isSuggestionsVisible, setIsSuggestionsVisible] = useState(false)

    console.log(customSpecies)

    const handleChange = (e: { target: { value: string } }) => {
        const value = e.target.value
        setCustomSpecies(value)

        if (value) {
            const filtered = suggestions.filter((suggestion) =>
                suggestion.toLowerCase().startsWith(value.toLowerCase())
            )
            setFilteredSuggestions(filtered)
            setIsSuggestionsVisible(true)
        } else {
            setFilteredSuggestions([])
            setIsSuggestionsVisible(false)
        }
    }

    const handleSuggestionClick = (suggestion: string) => {
        setCustomSpecies(suggestion)
        setFilteredSuggestions([])
        setIsSuggestionsVisible(false)
    }

    const handleBlur = (e: { relatedTarget: Node | null }) => {
        // Check if the blur event is happening because of a click inside the suggestions container
        if (
            (suggestionsContainerRef.current) &&
            !(
                suggestionsContainerRef.current
            ).contains(e.relatedTarget)
        ) {
            setIsSuggestionsVisible(false)
        }
    }

    return (
        <div className="relative" onBlur={handleBlur}>
            <Input
                type="text"
                value={customSpecies}
                onChange={handleChange}
                className="w-full ml-2 p-1 transition duration-100 text-center"
                placeholder="species_type"
            />
            {isSuggestionsVisible && filteredSuggestions.length > 0 && (
                <ul
                    ref={suggestionsContainerRef}
                    className="absolute left-4 right-0 mt-1 bg-black rounded shadow-lg transition duration-300 list-none"
                    onMouseDown={(e) => e.preventDefault()} // Prevents the input from losing focus when clicking on suggestions
                >
                    {filteredSuggestions.map((suggestion, index) => (
                        <li
                            key={index}
                            onClick={() => handleSuggestionClick(suggestion)}
                            className="px-4 py-2 cursor-pointer hover:bg-gray-800 transition duration-100 text-center text-sm rounded-lg"
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
