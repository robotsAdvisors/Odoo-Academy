# Plan Funcional y Técnico - Nivel 0 Interactivo (Fundador Digital)

## Objetivo del diseño
Construir una experiencia interactiva dentro de eLearning (Odoo Community) para el Nivel 0, común para Ecommerce y Hostelería, donde el alumno:

1. Ve el contenido del nivel.
2. Toma decisiones con botones (flujo guiado y ramificado).
3. Recibe una propuesta lógica según sus respuestas.
4. Genera automáticamente un PDF con decisiones y recomendación.
5. Obtiene puntos por completar.
6. Desbloquea automáticamente el Nivel 1 de Ecommerce o Hostelería.

## Alcance inicial (MVP)
Incluye solo Nivel 0 y solo idioma español.

Incluye:
1. Motor de decisiones interactivo con botones.
2. Resultado automático por reglas.
3. Generación de PDF de diagnóstico.
4. Asignación de puntos en gamificación.
5. Desbloqueo del curso de Nivel 1 según ruta recomendada.

No incluye en esta fase:
1. Multiidioma.
2. Editor visual avanzado de árboles de decisión.
3. Certificados con firma digital.

## Experiencia dentro de eLearning
### Flujo de usuario
1. Alumno entra al curso Nivel 0 en website_slides.
2. Consume video/lecciones base.
3. Abre la actividad interactiva Fundador Digital (botones por pregunta).
4. Responde preguntas y avanza por ramificación.
5. Finaliza y ve pantalla de resultado:
   - Recomendación Community vs Enterprise.
   - Recomendación de arquitectura (Online, Docker, Azure, Odoo.sh, Hosting).
   - Ruta sugerida (Ecommerce o Hostelería).
   - Checklist final según ruta recomendada.
   - Lista de módulos recomendados según respuestas.
   - Diagnóstico contextual que explique por qué se recomiendan esos módulos.
6. Pulsa Generar PDF.
7. Se genera y adjunta PDF con su diagnóstico.
8. Se otorgan puntos.
9. Se desbloquea automáticamente el Nivel 1 correspondiente.

### UX esperada
1. Interfaz tipo wizard web dentro del frontend de Odoo (no backend técnico).
2. Botones grandes por opción, con feedback inmediato.
3. Barra de progreso.
4. Pantalla final clara con CTA:
   - Descargar PDF.
   - Ir al Nivel 1 desbloqueado.

### Resultado esperado para el alumno
La pantalla final no debe limitarse a informar la ruta sugerida. Debe entregar un resultado accionable y entendible:

1. Ruta recomendada: Ecommerce o Hostelería.
2. Checklist base de esa ruta dividido en:
   - Obligatorios.
   - Recomendados.
   - Avanzados.
3. Ajustes del checklist según respuestas del diagnóstico.
4. Explicación breve por cada módulo disparado por el caso.
5. Próximo paso claro: avanzar al Nivel 1 desbloqueado.

El mismo resultado debe replicarse en el PDF final para que el alumno conserve una hoja de ruta concreta.

## Diseño funcional
### Entidades nuevas propuestas
1. academy.decision.flow
   - Define un flujo (ejemplo: Fundador Digital Nivel 0).
2. academy.decision.question
   - Preguntas del flujo, orden, tipo y texto.
3. academy.decision.option
   - Opciones por pregunta (texto de botón, puntajes, siguiente pregunta).
4. academy.decision.session
   - Intento de un alumno (estado, usuario, resultado final).
5. academy.decision.answer
   - Respuestas elegidas por sesión.
6. academy.decision.result.rule
   - Reglas para mapear respuestas/puntajes a recomendaciones.
7. academy.decision.checklist.item
   - Ítems configurables por ruta (obligatorio, recomendado, avanzado), con condición opcional de activación.

### Comportamiento funcional del resultado
El motor de resultado debe construir una salida compuesta por cuatro bloques:

1. Recomendación de edición.
2. Recomendación de arquitectura.
3. Ruta sugerida.
4. Checklist final contextualizado.

El checklist final contextualizado se calcula en dos capas:

1. Capa base por ruta.
   - Ecommerce carga su checklist base.
   - Hostelería carga su checklist base.
2. Capa condicional por respuestas.
   - Activa módulos adicionales o cambia prioridad de ciertos módulos.
   - Añade una justificación breve visible para el alumno.

Esto evita que el resultado final sea solo un texto estático y permite que el alumno reciba una recomendación distinta aunque dos usuarios compartan la misma ruta principal.

### Integración con gamificación actual
Reusar academy.gamification.mission para otorgar puntos al finalizar sesión.

Nueva misión automática propuesta:
1. Nombre: Nivel 0 completado - Fundador Digital.
2. Puntos base: 250.
3. Bonus opcional por calidad (fase posterior): +100.

Control de duplicados:
1. source_key único por usuario y flujo.

### Reglas de desbloqueo Nivel 1
Resultado de la sesión define ruta:
1. Ruta Ecommerce: enrolar miembro en canal Nivel 1 Ecommerce.
2. Ruta Hostelería: enrolar miembro en canal Nivel 1 Hostelería.

Implementación técnica de desbloqueo:
1. Crear/actualizar relación en slide.channel.partner para el usuario.
2. Estado mínimo: joined.
3. Verificar existencia previa para no duplicar.

## Diseño de PDF
### Contenido mínimo del PDF
1. Datos del alumno (nombre, fecha).
2. Resumen de respuestas.
3. Resultado recomendado:
   - Edición recomendada.
   - Arquitectura recomendada.
   - Ruta recomendada (Ecommerce/Hostelería).
   - Checklist final por ruta.
   - Módulos sugeridos y motivo de inclusión.
4. Próximos pasos (plan 30 días resumido).

### Implementación técnica
1. Reporte QWeb PDF sobre academy.decision.session.
2. Botón generar PDF en resultado final.
3. Adjuntar en ir.attachment.
4. Exponer descarga desde frontend.

## Reglas de decisión (base)
### Bloque 1: Edición
Variables guía:
1. Presupuesto.
2. Necesidad de personalización profunda.
3. Disponibilidad de equipo técnico.

Resultado:
1. Más peso técnico/personalización -> Community.
2. Más peso rapidez/soporte estándar -> Enterprise.

### Bloque 2: Arquitectura
Variables guía:
1. Tiempo de salida.
2. Complejidad técnica aceptable.
3. Necesidad de control y escalabilidad.

Resultado:
1. Rápido y simple -> Odoo Online/gestionado.
2. Personalización y control -> Docker/Azure/Odoo.sh.

### Bloque 3: Ruta de aprendizaje
Variables guía:
1. Tipo de negocio principal.
2. Operación de tienda online vs operación restaurante.

Resultado:
1. Comercio online -> Nivel 1 Ecommerce.
2. Restaurante/servicio en mesa/TPV -> Nivel 1 Hostelería.

### Bloque 4: Checklist contextual por ruta
Una vez determinada la ruta principal, el sistema debe resolver el checklist final que verá el alumno.

#### Ruta Ecommerce
Checklist base:
1. Obligatorios:
   - Ventas.
   - Contactos.
   - Website.
   - eCommerce.
   - Inventario.
   - Facturación.
2. Recomendados:
   - CRM.
   - Email Marketing.
   - Marketing Automation.
   - Live Chat.
   - WhatsApp (módulo externo).
3. Avanzados:
   - Suscripciones.
   - Helpdesk.
   - Programa de fidelización.
   - Conectores Amazon.
   - Conectores Shopify.

Reglas de ajuste por diagnóstico:
1. Si vende productos físicos -> Inventario se mantiene como obligatorio operativo.
2. Si vende servicios -> añadir Proyectos como recomendado.
3. Si realiza campañas -> activar Marketing Automation como recomendado activo.
4. Si gestiona soporte -> activar Helpdesk.

#### Ruta Hostelería
Checklist base:
1. Obligatorios:
   - Contactos.
   - Ventas.
   - Compras.
   - Inventario.
   - Facturación.
   - Punto de Venta (POS).
2. Recomendados:
   - CRM.
   - Marketing Email.
   - Programa de Fidelización.
   - Eventos.
3. Avanzados:
   - Reservas.
   - Kitchen Display.
   - Integración Delivery.
   - WhatsApp IA.
   - Automatizaciones n8n.

Reglas de ajuste por diagnóstico:
1. Si opera reservas -> activar Reservas.
2. Si tiene cocina con múltiples estaciones -> activar Kitchen Display.
3. Si trabaja con reparto -> activar Integración Delivery.
4. Si quiere automatizar atención o captación -> activar WhatsApp IA y automatizaciones.

### Formato de entrega del resultado
La salida final debe mostrar cada ítem con un estado visible para el alumno:

1. Base de la ruta.
2. Activado por tu caso.
3. Recomendado para fase posterior.

De esta forma el alumno entiende qué debe implementar ahora y qué puede dejar para una etapa siguiente.

## Arquitectura técnica propuesta (Community)
1. Modelos en módulo academy_gamification para decisiones y sesiones.
2. Controlador web para experiencia interactiva dentro del sitio eLearning.
3. Plantillas QWeb para interfaz de preguntas y pantalla de resultado.
4. Reporte QWeb PDF para el diagnóstico.
5. Hook de finalización para:
   - crear misión de puntos,
   - desbloquear canal de Nivel 1.

## Seguridad y permisos
1. Lectura de flujo/preguntas para usuarios del portal/alumnos inscritos.
2. Escritura de sesión/respuestas solo por dueño de sesión o sudo controlado.
3. Reglas backend para admin/formadores en mantenimiento de preguntas.

## Métricas mínimas (MVP)
1. Cantidad de alumnos que finalizan Nivel 0.
2. Distribución de ruta recomendada (Ecommerce vs Hostelería).
3. Tasa de conversión a Nivel 1 desbloqueado.

## Plan de implementación por fases
### Fase 1 - Base interactiva
1. Crear modelos de flujo, preguntas, opciones, sesiones y respuestas.
2. Crear interfaz web con botones y navegación.
3. Guardar respuestas por sesión.

### Fase 2 - Motor de resultado
1. Implementar reglas de recomendación.
2. Mostrar pantalla final con recomendaciones, checklist contextual y siguientes pasos.

### Fase 2.1 - Plantillas de checklist por ruta
1. Configurar checklist base Ecommerce.
2. Configurar checklist base Hostelería.
3. Configurar reglas condicionales de activación por respuestas.
4. Mostrar justificaciones cortas en el resultado final.

### Fase 3 - PDF
1. Crear plantilla QWeb del diagnóstico.
2. Generar y adjuntar PDF al finalizar con checklist contextualizado.
3. Exponer descarga al alumno.

### Fase 4 - Gamificación + desbloqueo
1. Otorgar puntos por finalización.
2. Desbloquear Nivel 1 por ruta.
3. Validar idempotencia (sin duplicados).

### Fase 5 - QA funcional
1. Pruebas de punta a punta con alumno demo.
2. Verificación de desbloqueo correcto.
3. Verificación de PDF y puntos.

## Riesgos y mitigaciones
1. Riesgo: complejidad de ramificación en primera versión.
   - Mitigación: iniciar con árbol limitado y ampliar luego.
2. Riesgo: desbloqueos duplicados.
   - Mitigación: llaves únicas y validaciones previas.
3. Riesgo: PDF sin contexto útil.
   - Mitigación: plantilla con resumen accionable y próximos pasos.

## Criterio de éxito del MVP
1. Alumno completa experiencia en menos de 10 minutos.
2. Obtiene recomendación coherente y PDF descargable.
3. Recibe checklist útil según su ruta y su caso real.
4. Recibe puntos.
5. Queda desbloqueado automáticamente un único Nivel 1.

## Decisiones cerradas para esta fase
1. Nivel: solo Nivel 0.
2. Idioma: español.
3. Plataforma: Odoo Community.
4. Experiencia: dentro de eLearning frontend.
5. Salida: PDF + puntos + desbloqueo de ruta.

## Próximo paso sugerido
Si este diseño te parece bien, se inicia implementación Fase 1 y Fase 2 en el módulo academy_gamification y luego se despliega a VPS para prueba funcional contigo.
