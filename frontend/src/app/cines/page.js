import { CINES_INFO } from "@/data/cines";
import TodayHeader from "@/components/TodayHeader";

export const metadata = {
  title: "Cines y Precios - FPS24",
  description: "Consulta los precios y el día del espectador de los cines independientes de Madrid.",
};

export default function CinesPage() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      
      <TodayHeader />

      {/* --- 2. CABECERA DE LA PÁGINA --- */}
      <div className="mb-12">
        
        {/* Contenedor centralizado (para alinear con el grid de abajo) */}
        <div className="max-w-6xl mx-auto px-6">
          
          {/* TÍTULO Y DESCRIPCIÓN (Centrados) */}
          <div className="text-center">
            <h2 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground mb-4">
              Salas y <span className="text-primary">Precios</span>
            </h2>
            <p className="text-muted text-lg max-w-2xl mx-auto">
              Guía rápida para saber cuánto cuesta ir al cine en Madrid y qué día es más barato en cada sala.
            </p>
          </div>

        </div>
      </div>

      {/* --- 3. GRID DE CINES --- */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {CINES_INFO.map((cine) => (
                <div key={cine.id} className="bg-background rounded-2xl border border-line overflow-hidden hover:border-primary transition-colors group flex flex-col">
                    
                    {/* Nombre del Cine */}
                    <div className="p-6 border-b border-line">
                        <h3 className="text-xl font-bold font-display text-foreground mb-1">
                            {cine.nombre}
                        </h3>
                        <div className="flex items-center gap-2 text-xs text-muted">
                             {cine.direccion}
                        </div>
                    </div>

                    {/* Precios */}
                    <div className="p-6 space-y-5 flex-grow">
                        
                        {/* Entrada Normal */}
                        <div className="flex justify-between items-start">
                            <span className="text-muted text-sm font-medium">Entrada Normal</span>
                            <span className="text-lg font-bold text-foreground text-right leading-tight">{cine.precio_normal}</span>
                        </div>

                        {/* Separador */}
                        <div className="h-px bg-line w-full"></div>

                        {/* Día del Espectador (Destacado) */}
                        <div className="bg-accent-soft border border-accent rounded-xl p-4 relative overflow-hidden">
                            <div className="flex justify-between items-center mb-2 relative z-10">
                                <span className="text-foreground text-[10px] font-black uppercase tracking-widest border border-accent px-2 py-0.5 rounded-full bg-accent">
                                    Día del Espectador
                                </span>
                            </div>
                            <div className="flex justify-between items-end relative z-10">
                                <span className="text-foreground font-bold text-sm">{cine.dia_espectador}</span>
                                <span className="text-2xl font-black text-primary">{cine.precio_espectador}</span>
                            </div>
                        </div>

                        {/* Notas extra */}
                        {cine.notas && (
                            <p className="text-xs text-muted italic leading-relaxed border-t border-line pt-4">
                                {cine.notas}
                            </p>
                        )}
                    </div>

                    {/* Botón Web (Pie de tarjeta) */}
                    <div className="p-4 bg-surface border-t border-line">
                        <a 
                            href={cine.web} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="block w-full text-center py-2.5 rounded-lg bg-background border border-line hover:border-primary hover:text-primary text-sm text-foreground font-bold transition-colors"
                        >
                            Visitar Web Oficial ↗
                        </a>
                    </div>

                </div>
            ))}

        </div>
      </div>

    </main>
  );
}