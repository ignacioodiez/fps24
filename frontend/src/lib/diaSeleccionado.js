// Día elegido en la portada, para que la vista rápida muestre primero sus sesiones.
// Estado de módulo: sobrevive a la navegación en cliente (la portada sigue montada bajo el modal), no a recargar.
let dia = null;

export const guardarDia = (fecha) => {
  dia = fecha;
};

export const diaGuardado = () => dia;
