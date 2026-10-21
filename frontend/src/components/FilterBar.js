export default function FilterBar({ 
  onlySpecials, 
  setOnlySpecials, 
  searchTerm, 
  setSearchTerm 
}) {
  return (
    <div className="flex flex-col sm:flex-row gap-4 w-full xl:w-auto">
      <button
        onClick={() => setOnlySpecials(!onlySpecials)}
        className={`
          h-14 px-6 rounded-2xl font-semibold transition-colors flex items-center justify-center gap-2 text-sm md:text-base border w-full sm:w-auto
          ${onlySpecials 
            ? "bg-primary text-white border-primary" 
            : "bg-background text-foreground border-line hover:bg-surface"}
        `}
      >
        {onlySpecials ? "ESPECIALES" : "VER ESPECIALES"}
      </button>

      <div className="relative w-full sm:w-64 group">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-muted group-focus-within:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          placeholder="Buscar película..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="block w-full h-14 pl-10 pr-3 rounded-2xl bg-background border border-line text-foreground placeholder-muted focus:outline-none focus:border-primary transition-colors"
        />
        {searchTerm && (
          <button 
            onClick={() => setSearchTerm("")}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-foreground"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}