import Markdown from "react-markdown"
import { readFileSync } from "fs"

export default function HomePage() {
    const markdown = readFileSync(
        `${process.cwd()}/src/content/HomePage.md`,
        "utf-8"
    )
    return (
        <div className="flex-col justify-center">
            <Markdown>{markdown}</Markdown>
        </div>
    )
}
