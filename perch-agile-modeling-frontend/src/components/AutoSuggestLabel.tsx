import { useState } from "react"
import AutoSuggest from "react-autosuggest"

export default function AutoSuggestLabel(
    this: any,
    {
        label,
        setLabel,
        suggestions,
    }: {
        label: string
        setLabel: (label: string) => void
        suggestions: string[]
    }
) {
    const [value, setValue] = useState(label)
    const [suggestionsList, setSuggestionsList] = useState<string[]>([])

    function getSuggestions(value: string) {
        const inputValue = value.trim().toLowerCase()
        const inputLength = inputValue.length

        return inputLength === 0
            ? []
            : suggestions.filter(
                  (suggestion) =>
                      suggestion.toLowerCase().slice(0, inputLength) ===
                      inputValue
              )
    }

    function onSuggestionsFetchRequested({ value }: { value: string }) {
        setSuggestionsList(getSuggestions(value))
    }

    function onSuggestionsClearRequested() {
        setSuggestionsList([])
    }

    function onSuggestionSelected(
        event: React.FormEvent<HTMLFormElement>,
        { suggestion }: { suggestion: string }
    ) {
        setLabel(suggestion)
    }

    function onChange(
        event: React.FormEvent<HTMLInputElement>,
        { newValue }: { newValue: string }
    ) {
        setValue(newValue)
    }

    const inputProps = {
        placeholder: "Label",
        value,
        onChange: this.onChange,
    }

    return (
        <AutoSuggest
            suggestions={suggestionsList}
            onSuggestionsFetchRequested={onSuggestionsFetchRequested}
            onSuggestionsClearRequested={onSuggestionsClearRequested}
            onSuggestionSelected={onSuggestionSelected}
            getSuggestionValue={(suggestion) => suggestion}
            renderSuggestion={(suggestion) => <div>{suggestion}</div>}
            inputProps={inputProps}
        />
    )
}
