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
          h-14 px-6 rounded-2xl font-semibold transition-all shadow-xl flex items-center justify-center gap-2 text-sm md:text-base border w-full sm:w-auto
          ${onlySpecials 
            ? "bg-purple-600 text-white border-purple-400 shadow-purple-500/50 ring-2 ring-purple-400/30" 
            : "bg-gray-800/50 text-gray-300 hover:bg-gray-700 border-gray-700 hover:border-gray-500 hover:text-white backdrop-blur-sm"}
        `}
      >
        {onlySpecials ? "⭐  ESPECIALES" : "⭐ VER ESPECIALES"}
      </button>

      <div className="relative w-full sm:w-64 group">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-yellow-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          placeholder="Buscar película..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="block w-full h-14 pl-10 pr-3 rounded-2xl bg-gray-800/50 border border-gray-700 text-gray-300 placeholder-gray-500 focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 focus:text-white transition-all backdrop-blur-sm"
        />
        {searchTerm && (
          <button 
            onClick={() => setSearchTerm("")}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-white"
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