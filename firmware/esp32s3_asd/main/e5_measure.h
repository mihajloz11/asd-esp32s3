#ifndef E5_MEASURE_H
#define E5_MEASURE_H
#include <stdbool.h>
#ifdef ASD_E5_MEASURE
void e5_measure_start(int address);
bool e5_measure_command(const char *command);
#else
static inline void e5_measure_start(int address) { (void)address; }
static inline bool e5_measure_command(const char *command) { (void)command; return false; }
#endif
#endif
