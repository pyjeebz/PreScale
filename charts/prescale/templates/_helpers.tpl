{{/*
Expand the name of the chart.
*/}}
{{- define "prescale.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "prescale.fullname" -}}
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
{{- define "prescale.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "prescale.labels" -}}
helm.sh/chart: {{ include "prescale.chart" . }}
{{ include "prescale.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "prescale.selectorLabels" -}}
app.kubernetes.io/name: {{ include "prescale.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "prescale.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "prescale.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Inference service fullname
*/}}
{{- define "prescale.inference.fullname" -}}
{{- printf "%s-inference" (include "prescale.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Cost Intelligence service fullname
*/}}
{{- define "prescale.costIntelligence.fullname" -}}
{{- printf "%s-cost-intelligence" (include "prescale.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Inference image
*/}}
{{- define "prescale.inference.image" -}}
{{- $tag := default .Chart.AppVersion .Values.inference.image.tag }}
{{- printf "%s:%s" .Values.inference.image.repository $tag }}
{{- end }}

{{/*
Cost Intelligence image
*/}}
{{- define "prescale.costIntelligence.image" -}}
{{- $tag := default .Chart.AppVersion .Values.costIntelligence.image.tag }}
{{- printf "%s:%s" .Values.costIntelligence.image.repository $tag }}
{{- end }}
