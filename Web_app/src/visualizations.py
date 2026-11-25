import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

# Consistent color palette adhering to scientific presentation standards
PALETTE = {
    'protein': '#2b5c8f',
    'carbs': '#d97724',
    'fat': '#438a5e',
    'calories': '#1f4e79',
    'fiber': '#5b9279',
    'sugar': '#c0392b',
    'sodium': '#7f8c8d',
    'background': '#f8f9fa'
}


def plot_macronutrient_donut(macro_energy_pct: Dict[str, float], title: str = "Macronutrient Energy Distribution") -> go.Figure:
    # Build an interactive donut chart illustrating caloric contribution by macronutrient
    labels = ['Protein', 'Carbohydrates', 'Total Fat']
    values = [
        macro_energy_pct.get('protein_pct', 0.0),
        macro_energy_pct.get('carbs_pct', macro_energy_pct.get('carb_pct', 0.0)),
        macro_energy_pct.get('fat_pct', 0.0)
    ]
    colors = [PALETTE['protein'], PALETTE['carbs'], PALETTE['fat']]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
        textinfo='label+percent',
        hoverinfo='label+percent+value',
        textfont=dict(size=13, family='Arial')
    )])

    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color='#2c3e50', family='Arial')),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5),
        margin=dict(l=20, r=20, t=40, b=30),
        height=320
    )
    return fig


def plot_nutrient_comparison_bar(actual: Dict[str, float], targets: Dict[str, float]) -> go.Figure:
    # Generate grouped comparison bar chart for meal nutrients against target allowances
    nutrients = ['Calories (kcal)', 'Protein (g)', 'Carbs (g)', 'Fat (g)', 'Fiber (g)']
    actual_vals = [
        actual.get('energy_kcal', 0.0),
        actual.get('protein_g', 0.0),
        actual.get('carbohydrate_g', 0.0),
        actual.get('fat_g', 0.0),
        actual.get('dietary_fiber_g', 0.0)
    ]
    target_vals = [
        targets.get('calories', 0.0),
        targets.get('protein_g', 0.0),
        targets.get('carbs_g', 0.0),
        targets.get('fat_g', 0.0),
        targets.get('fiber_g', 0.0)
    ]

    fig = go.Figure(data=[
        go.Bar(name='Current Meal', x=nutrients, y=actual_vals, marker_color='#2b5c8f'),
        go.Bar(name='Meal Target Budget', x=nutrients, y=target_vals, marker_color='#95a5a6')
    ])

    fig.update_layout(
        barmode='group',
        title=dict(text='Meal Nutrient Intake vs Target Budget', font=dict(size=15, color='#2c3e50')),
        xaxis=dict(title='Nutrient Metric'),
        yaxis=dict(title='Quantity'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=30, r=20, t=50, b=40),
        height=350
    )
    return fig


def plot_amdr_comparison(actual_pct: Dict[str, float], amdr_ranges: Dict[str, Any]) -> go.Figure:
    # Visualize actual macronutrient percentages against WHO/IOM AMDR acceptable ranges
    macros = ['Protein', 'Carbohydrates', 'Fat']
    actual_vals = [
        actual_pct.get('protein_pct', 0.0),
        actual_pct.get('carbs_pct', actual_pct.get('carb_pct', 0.0)),
        actual_pct.get('fat_pct', 0.0)
    ]

    def _extract_bounds(val):
        if isinstance(val, dict):
            return float(val.get('min', 0.0)), float(val.get('max', 100.0))
        elif isinstance(val, (list, tuple)):
            return float(val[0]), float(val[1])
        return 0.0, 100.0

    p_min, p_max = _extract_bounds(amdr_ranges.get('protein', (10.0, 35.0)))
    c_min, c_max = _extract_bounds(amdr_ranges.get('carbs', (45.0, 65.0)))
    f_min, f_max = _extract_bounds(amdr_ranges.get('fat', (20.0, 35.0)))

    min_vals = [p_min, c_min, f_min]
    max_vals = [p_max, c_max, f_max]

    fig = go.Figure()

    # Add acceptable range horizontal bars
    for i, m in enumerate(macros):
        fig.add_trace(go.Bar(
            y=[m],
            x=[max_vals[i] - min_vals[i]],
            base=[min_vals[i]],
            orientation='h',
            name='AMDR Acceptable Range' if i == 0 else None,
            showlegend=(i == 0),
            marker=dict(color='rgba(46, 117, 89, 0.25)', line=dict(color='#2e7559', width=1))
        ))

    # Add scatter markers for actual meal values
    fig.add_trace(go.Scatter(
        y=macros,
        x=actual_vals,
        mode='markers',
        name='Current Meal %',
        marker=dict(color='#c0392b', size=14, symbol='diamond')
    ))

    fig.update_layout(
        title=dict(text='Macronutrient % vs AMDR Guidelines', font=dict(size=15, color='#2c3e50')),
        xaxis=dict(title='Percentage of Total Energy (%)', range=[0, 100]),
        yaxis=dict(title='Macronutrient'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=20, t=50, b=40),
        height=280
    )
    return fig


def plot_daily_intake_trend(daily_data: List[Dict[str, Any]], target_calories: float = 2000.0) -> go.Figure:
    # Plot historical daily calorie intake against target reference line
    if not daily_data:
        fig = go.Figure()
        fig.update_layout(title="No Historical Intake Records Found", height=300)
        return fig

    dates = [d['date'] for d in daily_data]
    cals = [d['total_calories'] for d in daily_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=cals,
        mode='lines+markers',
        name='Daily Calories',
        line=dict(color='#1f4e79', width=3),
        marker=dict(size=8, color='#1f4e79')
    ))

    fig.add_hline(
        y=target_calories,
        line_dash='dash',
        line_color='#c0392b',
        annotation_text=f"Daily Calorie Target ({int(target_calories)} kcal)",
        annotation_position="top right"
    )

    fig.update_layout(
        title=dict(text='Daily Energy Intake History', font=dict(size=15, color='#2c3e50')),
        xaxis=dict(title='Date'),
        yaxis=dict(title='Energy (kcal)'),
        margin=dict(l=30, r=20, t=40, b=40),
        height=320
    )
    return fig

