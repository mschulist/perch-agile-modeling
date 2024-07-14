import React, { useEffect, useRef, useState } from "react"
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
    const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1)

    const handleChange = (e: { target: { value: string } }) => {
        const value = e.target.value
        setCustomSpecies(value)

        if (value) {
            const filtered = suggestions.filter((suggestion) =>
                suggestion.toLowerCase().startsWith(value.toLowerCase())
            )
            setFilteredSuggestions(filtered.slice(0, 3))
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
            suggestionsContainerRef.current &&
            suggestionsContainerRef.current.contains(e.relatedTarget)
        ) {
            setIsSuggestionsVisible(false)
        }
    }

    const handleKeyDown = (e: { key: string; preventDefault: () => void }) => {
        if (e.key === "ArrowDown") {
            e.preventDefault() // Prevent the cursor from moving
            setSelectedSuggestionIndex((prevIndex) =>
                prevIndex < filteredSuggestions.length - 1
                    ? prevIndex + 1
                    : prevIndex
            )
        } else if (e.key === "ArrowUp") {
            e.preventDefault() // Prevent the cursor from moving
            setSelectedSuggestionIndex((prevIndex) =>
                prevIndex > 0 ? prevIndex - 1 : 0
            )
        } else if (e.key === "Enter" && selectedSuggestionIndex >= 0) {
            e.preventDefault()
            handleSuggestionClick(filteredSuggestions[selectedSuggestionIndex])
        }
    }

    // Automatically reset selection when suggestions change
    useEffect(() => {
        setSelectedSuggestionIndex(-1)
    }, [filteredSuggestions])

    return (
        <div className="relative z-10" onBlur={handleBlur}>
            <Input
                type="text"
                value={customSpecies}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                className="w-full p-1 transition duration-100 text-center"
                placeholder="species_type"
            />
            {isSuggestionsVisible && filteredSuggestions.length > 0 && (
                <ul
                    ref={suggestionsContainerRef}
                    className="absolute left-0 right-0 mt-1 bg-black rounded shadow-lg transition duration-300 list-none"
                    onMouseDown={(e) => e.preventDefault()}
                >
                    {filteredSuggestions.map((suggestion, index) => (
                        <li
                            key={index}
                            onClick={() => handleSuggestionClick(suggestion)}
                            className={`px-4 py-2 cursor-pointer hover:bg-gray-800 transition duration-100 text-center text-sm rounded-lg ${
                                index === selectedSuggestionIndex
                                    ? "bg-gray-800"
                                    : ""
                            }`}
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
