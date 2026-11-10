# CALVIN Failure Analysis

[简体中文](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/README.md) · [English](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.en.md) · [日本語](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.ja.md) · [Deutsch](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.fr.md) · **Español** · [Português](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/locales/README.pt.md)

¿En qué paso se atasca un robot cuando fallan todas las secuencias de cinco pasos? El estudio usa el simulador CALVIN y un modelo MCIL público para examinar desviaciones en las acciones y probar la recuperación tras un fallo. Incluye figuras, datos y un informe en chino.

Python · CALVIN · MCIL · [Ver informe del experimento](https://github.com/chenbinghan666/calvin-failure-analysis/blob/main/docs/report.pdf)

Este es un proyecto de investigación a pequeña escala basado en el entorno de simulación [CALVIN](https://github.com/mees/calvin) y el modelo oficial de preentrenamiento MCIL.

El proyecto se centra en las siguientes preguntas: **Cuando la tasa de éxito de una tarea de robot de larga distancia es 0, ¿dónde exactamente falla el robot, por qué falla y si puede recuperarse después de una falla?**

La tasa de éxito tradicional a nivel de tarea solo conserva el éxito o fracaso final y no puede distinguir entre las siguientes situaciones:

- El modelo no parte del primer paso;
- El modelo puede completar algunos pasos, pero los errores se acumulan en tareas posteriores;
- El modelo comprende la tarea, pero el control continuo se aleja gradualmente;
- El modelo sólo tiene éxito en unos pocos estados iniciales;
- El modelo no puede recuperarse por sí solo después de un fallo.

## Proceso experimental

1. Reproduzca la trayectoria de demostración real para verificar el entorno, el formato de acción y la determinación del éxito.
2. Se probaron tres tareas individuales: abrir el LED, mover la puerta corredera hacia la izquierda y abrir el cajón, respectivamente.
3. Ejecute 100 secuencias de programas fijas de cinco pasos y registre de SR@1 a SR@5.
4. Reemplace el vínculo de falla directa del posicionamiento a través de la posición, la actitud y la acción de la pinza.
5. Se corrigió el reintento y se continuaron los diagnósticos después del fallo.

## Resultados principales

| experimentar | resultado |
|---|---:|
| Encienda el LED | 2/9 |
| puerta corredera izquierda | 0/9 |
| cajón abierto | 0/9 |
| 100 secuencias de cinco pasos completadas con éxito | 0/100 |
| SR@1 | 1% |
| SR@2—SR@5 | 0% |
| Recuperación de reintento fijo | 0/10 |
| Continuar la ejecución después del fallo | 0/50 pasos |

Una condición de éxito del LED aún se completa en el paso de acción 94 después de ejecutarse de forma independiente, lo que indica que el modelo no es completamente incapaz, pero es sensible al estado inicial. La comparación de los componentes de la acción mostró que los tres tipos de tareas fallaron después de reemplazar únicamente la acción de posición; cuando se ejecuta libremente, la distancia entre la acción de posición y la trayectoria de demostración se expandió a 72,9-194,2 mm. La caja de LED también mostró una orientación inconsistente de la pinza en pasos clave.

Resultados experimentales a nivel de proceso ![](../../figures/process_level_results.png)

## Casos de éxito y fracaso

| Historias de éxito del LED: cómo empezar | Historia de éxito LED: Fin |
|---|---|
| ![](../../figures/led_success_start.png) | ![](../../figures/led_success_end.png) |

| Caso de falla del LED: cómo comenzar | Caso de falla del LED: después de ejecutar 360 pasos |
|---|---|
| ![](../../figures/led_failure_start.png) | ![](../../figures/led_failure_end.png) |

## Conclusión

Este experimento muestra que la tasa de éxito a nivel de tarea es adecuada para medir la finalización final, pero no es suficiente para explicar el proceso de fracaso de la tarea a largo plazo. Como mínimo, también se deben registrar el primer paso fallido, la duración continua de la finalización, la desviación del componente de movimiento y los resultados de la recuperación.

La evidencia actual respalda que "la desviación de posición de circuito cerrado es un vínculo directo de falla común a los tres tipos de tareas", pero no puede usarse para determinar la única causa dentro del modelo. Esta conclusión solo se aplica a los pesos públicos, los datos de depuración y las condiciones experimentales utilizadas en este proyecto.

## Estructura del proyecto

```text
.
├── README.md
├── docs/
│   ├── report.pdf                  # informe del laboratorio chino
│   └── internship-summary.md       # Resumen de prácticas de investigación científica.
├── figures/                        # Diagrama resumido y capturas de pantalla del caso.
├── results/                        # Resultados del experimento JSON frente a CSV
└── src/                            # Código de evaluación y diagnóstico.
```

Informe chino completo: [docs/report.pdf](../../docs/report.pdf)

Para la selección de preguntas de investigación, el trabajo completado por mí, el proceso de depuración y las limitaciones de la investigación durante la pasantía de investigación científica, consulte: [docs/internship-summary.md](../../docs/internship-summary.md)

## Instrucciones de reproducción

El código debe ejecutarse en el entorno oficial de CALVIN y prepararse:

- Entorno CALVIN con `calvin_models`;
- Datos del entorno D o datos de depuración oficiales;
- Punto de control oficial `D_D_static_rgb_baseline` MCIL;
- Python 3.8, PyTorch 1.13.1, PyTorch Lightning 1.8.6 e Hydra 1.1.1.

Entrada principal:

```bash
python src/run_calvin_mcil_cpu.py \
  --dataset-path /path/to/calvin_dataset \
  --train-folder /path/to/D_D_static_rgb_baseline \
  --checkpoint /path/to/mcil_baseline.ckpt \
  --num-sequences 100 \
  --output results/evaluation.json
```

Para fines de evaluación de una sola tarea y varios scripts de diagnóstico, consulte [src/README.md](../../src/README.md). Este repositorio no redistribuye el conjunto de datos de CALVIN ni las ponderaciones del modelo.

## límites de la investigación

- Sólo se probó un puesto de control público de MCIL;
- Utiliza ~1,3 GB de datos de depuración, no el conjunto de datos completo;
- Utilizando la inferencia de la CPU, no se realizaron experimentos con robots reales;
- Los resultados son estudios de etapa reproducibles y no representan los resultados de la clasificación oficial de CALVIN.

## Agradecimientos

Este proyecto utiliza el entorno de referencia CALVIN y sus modelos públicos. Respete la licencia del proyecto original y cite el documento de CALVIN cuando utilice datos, entornos o modelos relevantes:

> Mees et al., *CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks*, IEEE Robotics and Automation Letters, 2022.
