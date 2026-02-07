import Image from "next/image"

/**
 * Renders the user icon component.
 *
 * @returns The rendered user icon component.
 */
export default function UserIcon({ url }: { url: string }) {
    return (
        <div className="flex items-center">
            <Image
                src={url}
                alt="User icon"
                width={48}
                height={48}
                className="mx-4 rounded-lg"
            />
        </div>
    )
}
