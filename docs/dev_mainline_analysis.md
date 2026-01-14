# Mainline Analysis from kickoff

# Directed mainline (internal only) from kickoff
  - design_main_kickoff [done]
  - design_cli [planned]
  - design_feature_unit_graph [done]
  - design_meta_self_description [planned]
  - future_interactive_graph [imagined]
  - implement_cli [planned]
  - implement_feature_unit_graph [done]

# Completion (internal mainline): 42.9%

# Directed pending critical path (internal):
  -> design_cli [planned]
  -> implement_cli [planned]

# Weakly connected mainline (internal + external) from kickoff:
  - design_cli [internal] [planned]
  - design_feature_unit_graph [internal] [done]
  - design_main_kickoff [internal] [done]
  - design_meta_self_description [internal] [planned]
  - future_interactive_graph [internal] [imagined]
  - implement_cli [internal] [planned]
  - implement_feature_unit_graph [internal] [done]
  - src.am_core.graph.FeatureUnitGraph [internal] [done]

# External dependencies in this component:
  (none)
