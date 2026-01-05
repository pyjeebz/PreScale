{{/*
Expand the name of the chart.
*/}}
{{- define "helios.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "helios.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "helios.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "helios.labels" -}}
helm.sh/chart: {{ include "helios.chart" . }}
{{ include "helios.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "helios.selectorLabels" -}}
app.kubernetes.io/name: {{ include "helios.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "helios.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "helios.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Inference service fullname
*/}}
{{- define "helios.inference.fullname" -}}
{{- printf "%s-inference" (include "helios.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Cost Intelligence service fullname
*/}}
{{- define "helios.costIntelligence.fullname" -}}
{{- printf "%s-cost-intelligence" (include "helios.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Inference image
*/}}
{{- define "helios.inference.image" -}}
{{- $tag := default .Chart.AppVersion .Values.inference.image.tag }}
{{- printf "%s:%s" .Values.inference.image.repository $tag }}
{{- end }}

{{/*
Cost Intelligence image
*/}}
{{- define "helios.costIntelligence.image" -}}
{{- $tag := default .Chart.AppVersion .Values.costIntelligence.image.tag }}
{{- printf "%s:%s" .Values.costIntelligence.image.repository $tag }}
{{- end }}
