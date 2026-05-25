import { SearchBar } from './SearchBar'
import { SearchResults } from './SearchResults'

export function SearchView() {
  return (
    <div className="flex flex-col gap-4">
      <SearchBar />
      <SearchResults />
    </div>
  )
}
