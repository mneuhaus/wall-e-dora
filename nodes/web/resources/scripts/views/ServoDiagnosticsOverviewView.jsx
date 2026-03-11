import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import node from '../Node';
import { useAppContext } from '../contexts/AppContext';
import { normalizeDiagnosticsPayload } from '../utils/servoData';

import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Container,
  Group,
  Paper,
  Stack,
  Switch,
  Table,
  Text,
  Title,
} from '@mantine/core';

/**
 * ServoDiagnosticsOverviewView Component
 *
 * Displays side-by-side diagnostics for all attached servos so differences are
 * easy to spot without opening each servo individually.
 *
 * @component
 */
const ServoDiagnosticsOverviewView = () => {
  const { availableServos } = useAppContext();
  const [diagnosticsOverview, setDiagnosticsOverview] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showDifferencesOnly, setShowDifferencesOnly] = useState(false);

  const servoLookup = useMemo(
    () => new Map((availableServos || []).map((servo) => [Number.parseInt(servo.id, 10), servo])),
    [availableServos]
  );

  const requestOverview = () => {
    setDiagnosticsOverview([]);
    setError('');
    setIsLoading(true);
    node.emit('read_servo_diagnostics', [{ all: true }]);
  };

  useEffect(() => {
    const unsubscribe = node.on('servo_diagnostics', (event) => {
      const payloads = normalizeDiagnosticsPayload(event?.value)
        .map((entry) => ({
          ...entry,
          id: Number.parseInt(entry.id, 10),
        }))
        .filter((entry) => Number.isInteger(entry.id))
        .sort((left, right) => left.id - right.id);

      if (payloads.length === 0) {
        setError('No diagnostics payload was returned for the attached servos.');
        setIsLoading(false);
        return;
      }

      setDiagnosticsOverview(payloads);
      setIsLoading(false);
      setError('');
    });

    requestOverview();
    return unsubscribe;
  }, []);

  const formatDiagnosticValue = (value) => {
    if (Array.isArray(value)) {
      return value.join(' ');
    }

    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }

    if (typeof value === 'number') {
      return Number.isInteger(value) ? value : value.toFixed(2);
    }

    if (value === null || value === undefined || value === '') {
      return 'N/A';
    }

    return String(value);
  };

  const getServoLabel = (entry) => {
    const knownServo = servoLookup.get(entry.id);
    return knownServo?.alias ? `${knownServo.alias} (#${entry.id})` : `Servo #${entry.id}`;
  };

  const overviewUpdatedAt = diagnosticsOverview.length > 0
    ? new Date(
        Math.max(...diagnosticsOverview.map((entry) => Number(entry.timestamp || 0))) * 1000
      ).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '';

  const overviewFields = [
    {
      label: 'Alias',
      getValue: (entry) => entry.alias || servoLookup.get(entry.id)?.alias || 'Unassigned',
    },
    {
      label: 'Model',
      getValue: (entry) => entry.model?.name || 'Unknown',
    },
    {
      label: 'Model #',
      getValue: (entry) => entry.model?.model_number ?? 'N/A',
    },
    {
      label: 'Position',
      getValue: (entry) => entry.status?.position ?? 'N/A',
    },
    {
      label: 'Speed',
      getValue: (entry) => entry.status?.speed ?? 'N/A',
    },
    {
      label: 'Load',
      getValue: (entry) => entry.status?.load ?? 'N/A',
    },
    {
      label: 'Voltage',
      getValue: (entry) => (
        Number.isFinite(entry.status?.voltage) ? `${entry.status.voltage.toFixed(1)}V` : 'N/A'
      ),
    },
    {
      label: 'Temperature',
      getValue: (entry) => (
        Number.isFinite(entry.status?.temperature) ? `${entry.status.temperature}°C` : 'N/A'
      ),
    },
    {
      label: 'Moving',
      getValue: (entry) => (
        entry.status?.moving === undefined ? 'N/A' : (entry.status.moving ? 'Yes' : 'No')
      ),
    },
    {
      label: 'Mode',
      getValue: (entry) => entry.config?.mode_name || 'N/A',
    },
    {
      label: 'Baud',
      getValue: (entry) => (
        entry.config?.baud_rate_bps ? `${entry.config.baud_rate_bps} bps` : 'N/A'
      ),
    },
    {
      label: 'Min Angle',
      getValue: (entry) => entry.config?.min_angle ?? 'N/A',
    },
    {
      label: 'Max Angle',
      getValue: (entry) => entry.config?.max_angle ?? 'N/A',
    },
    {
      label: 'P Gain',
      getValue: (entry) => entry.config?.p_coefficient ?? 'N/A',
    },
    {
      label: 'D Gain',
      getValue: (entry) => entry.config?.d_coefficient ?? 'N/A',
    },
    {
      label: 'I Gain',
      getValue: (entry) => entry.config?.i_coefficient ?? 'N/A',
    },
    {
      label: 'CW Dead Zone',
      getValue: (entry) => entry.config?.cw_dead_zone ?? 'N/A',
    },
    {
      label: 'CCW Dead Zone',
      getValue: (entry) => entry.config?.ccw_dead_zone ?? 'N/A',
    },
    {
      label: 'Protection Current',
      getValue: (entry) => entry.config?.protection_current ?? 'N/A',
    },
    {
      label: 'Position Offset',
      getValue: (entry) => entry.config?.position_offset ?? 'N/A',
    },
    {
      label: 'EEPROM Locked',
      getValue: (entry) => (
        entry.config?.lock_state === undefined ? 'N/A' : (entry.config.lock_state ? 'Yes' : 'No')
      ),
    },
  ];

  const overviewRows = overviewFields
    .map((field) => {
      const values = diagnosticsOverview.map((entry) => formatDiagnosticValue(field.getValue(entry)));
      return {
        label: field.label,
        values,
        hasDifference: new Set(values).size > 1,
      };
    })
    .filter((row) => !showDifferencesOnly || row.hasDifference);

  return (
    <Container size="xl" py="md">
      <Paper radius="md" withBorder p="md">
        <Stack spacing="md">
          <Group justify="space-between" align="flex-start">
            <Group>
              <ActionIcon component={Link} to="/" variant="subtle" color="amber" radius="xl">
                <i className="fa-solid fa-arrow-left"></i>
              </ActionIcon>
              <Stack spacing={0}>
                <Title order={4}>Servo Diagnostics Overview</Title>
                <Text size="sm" c="dimmed">
                  Compare live telemetry and key EEPROM configuration fields across all attached servos.
                </Text>
              </Stack>
            </Group>
            <Group spacing="xs" align="center">
              {diagnosticsOverview.length > 0 && (
                <Badge color="amber" variant="light">
                  {diagnosticsOverview.length} servos
                </Badge>
              )}
              <Switch
                size="sm"
                color="amber"
                checked={showDifferencesOnly}
                onChange={(event) => setShowDifferencesOnly(event.currentTarget.checked)}
                label="Differences only"
              />
              <Button
                size="xs"
                color="amber"
                variant="light"
                onClick={requestOverview}
                loading={isLoading}
              >
                Refresh All
              </Button>
            </Group>
          </Group>

          {overviewUpdatedAt && !isLoading && !error && (
            <Text size="xs" c="dimmed">
              Updated {overviewUpdatedAt}
            </Text>
          )}

          {error && (
            <Text size="sm" c="red">{error}</Text>
          )}

          {isLoading && (
            <Text size="sm" c="dimmed">Reading diagnostics from all attached servos...</Text>
          )}

          {!isLoading && !error && diagnosticsOverview.length === 0 && (
            <Text size="sm" c="dimmed">No attached servos were available for overview diagnostics.</Text>
          )}

          {!isLoading && diagnosticsOverview.length > 0 && (
            <Box style={{ overflowX: 'auto' }}>
              <Table striped highlightOnHover withTableBorder withColumnBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th style={{ minWidth: 180 }}>Field</Table.Th>
                    {diagnosticsOverview.map((entry) => (
                      <Table.Th key={entry.id} style={{ minWidth: 180 }}>
                        <Stack spacing={0}>
                          <Text
                            size="sm"
                            fw={600}
                            component={Link}
                            to={`/servo/${entry.id}`}
                            style={{ textDecoration: 'none', color: 'inherit' }}
                          >
                            {getServoLabel(entry)}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {entry.model?.name || 'Unknown model'}
                          </Text>
                        </Stack>
                      </Table.Th>
                    ))}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {overviewRows.map((row) => (
                    <Table.Tr
                      key={row.label}
                      style={row.hasDifference ? { backgroundColor: 'rgba(255, 179, 0, 0.08)' } : undefined}
                    >
                      <Table.Td style={{ fontWeight: 500 }}>{row.label}</Table.Td>
                      {row.values.map((value, index) => (
                        <Table.Td
                          key={`${row.label}-${diagnosticsOverview[index]?.id || index}`}
                          style={row.hasDifference ? { color: 'var(--mantine-color-amber-filled)' } : undefined}
                        >
                          {value}
                        </Table.Td>
                      ))}
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Box>
          )}

          {!isLoading && !error && diagnosticsOverview.length > 0 && overviewRows.length === 0 && showDifferencesOnly && (
            <Text size="sm" c="dimmed">No differences found across the compared diagnostics fields.</Text>
          )}
        </Stack>
      </Paper>
    </Container>
  );
};

export default ServoDiagnosticsOverviewView;
