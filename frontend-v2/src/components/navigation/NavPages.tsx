import Link from 'next/link'

export function NavPages() {
  return (
    <div className='navbar-center lg:flex z-10'>
      <ul className='menu menu-horizontal px-1 text-lg'>
        <li>
          <details>
            <summary>Pre-processing</summary>
            <ul className='p-2'>
              <li>
                <Link href='/preprocessing/embedding'>Embedding</Link>
              </li>
              <li>
                <Link href='/preprocessing/search'>Search</Link>
              </li>
            </ul>
          </details>
        </li>
        <li>
          <Link href='/annotate'>Annotate</Link>
        </li>
        <li>
          <Link href='/examine-annotations'>Examine Annotations</Link>
        </li>
        <li>
          <Link href='/summary'>Summary</Link>
        </li>
      </ul>
    </div>
  )
}
