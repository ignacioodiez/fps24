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
              whitespace-nowrap px-6 py-3 rounded-xl font-bold text-sm md:text-base transition-colors border
              ${selectedCinema === cine
                ? "bg-primary text-white border-primary"
                : "bg-background text-foreground border-line hover:bg-surface"
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