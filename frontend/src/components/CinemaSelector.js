import { cleanCinemaName } from "@/utils/helpers";

export default function CinemaSelector({ 
  availableCinemas, 
  selectedCinema, 
  setSelectedCinema 
}) {
  return (
    <div className="mt-8 mb-10 max-w-9xl mx-auto">
      <div className="flex gap-3 overflow-x-auto pb-4 px-2 md:px-0 custom-scrollbar">
        {availableCinemas.map((cine, index) => (
          <button
            key={index}
            onClick={() => setSelectedCinema(cine)}
            className={`
              whitespace-nowrap px-6 py-3 rounded-xl font-bold text-sm md:text-base transition-all duration-300 border
              ${selectedCinema === cine
                ? "bg-yellow-400 text-black border-yellow-300 shadow-lg shadow-yellow-400/20 scale-105"
                : "bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700 hover:text-white hover:border-gray-500"
              }
            `}
          >
            {cleanCinemaName(cine)}
          </button>
        ))}
      </div>
    </div>
  );
}