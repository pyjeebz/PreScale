"""Journeys: a user's path through the app (log in, search, add to cart, order),
saved as the HTTP requests it makes, so PreScale can replay it.

A journey lives in the app's own repo as `prescale/journeys/<name>.yaml`.
`model` loads and checks those files; `replay` runs a journey's steps.
"""
