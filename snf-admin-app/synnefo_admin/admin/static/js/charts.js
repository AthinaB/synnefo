$(document).ready(function() {
		/**
	 * Dark theme for Highcharts JS
	 * @author Torstein Honsi
	 */

	// Load the fonts
	Highcharts.createElement('link', {
	   href: 'http://fonts.googleapis.com/css?family=Unica+One',
	   rel: 'stylesheet',
	   type: 'text/css'
	}, null, document.getElementsByTagName('head')[0]);

	Highcharts.theme = {
	   colors: ["#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee",
	      "#55BF3B", "#DF5353", "#7798BF", "#aaeeee"],
	   chart: {
	      backgroundColor: {
	         linearGradient: { x1: 0, y1: 0, x2: 1, y2: 1 },
	         stops: [
	            [0, '#2a2a2b'],
	            [1, '#3e3e40']
	         ]
	      },
	      style: {
	         fontFamily: "'Unica One', sans-serif"
	      },
	      plotBorderColor: '#606063'
	   },
	   title: {
	      style: {
	         color: '#E0E0E3',
	         textTransform: 'uppercase',
	         fontSize: '20px'
	      }
	   },
	   subtitle: {
	      style: {
	         color: '#E0E0E3',
	         textTransform: 'uppercase'
	      }
	   },
	   xAxis: {
	      gridLineColor: '#707073',
	      labels: {
	         style: {
	            color: '#E0E0E3'
	         }
	      },
	      lineColor: '#707073',
	      minorGridLineColor: '#505053',
	      tickColor: '#707073',
	      title: {
	         style: {
	            color: '#A0A0A3'

	         }
	      }
	   },
	   yAxis: {
	      gridLineColor: '#707073',
	      labels: {
	         style: {
	            color: '#E0E0E3'
	         }
	      },
	      lineColor: '#707073',
	      minorGridLineColor: '#505053',
	      tickColor: '#707073',
	      tickWidth: 1,
	      title: {
	         style: {
	            color: '#A0A0A3'
	         }
	      }
	   },
	   tooltip: {
	      backgroundColor: 'rgba(0, 0, 0, 0.85)',
	      style: {
	         color: '#F0F0F0'
	      }
	   },
	   plotOptions: {
	      series: {
	         dataLabels: {
	            color: '#B0B0B3'
	         },
	         marker: {
	            lineColor: '#333'
	         }
	      },
	      boxplot: {
	         fillColor: '#505053'
	      },
	      candlestick: {
	         lineColor: 'white'
	      },
	      errorbar: {
	         color: 'white'
	      }
	   },
	   legend: {
	      itemStyle: {
	         color: '#E0E0E3'
	      },
	      itemHoverStyle: {
	         color: '#FFF'
	      },
	      itemHiddenStyle: {
	         color: '#606063'
	      }
	   },
	   credits: {
	      style: {
	         color: '#666'
	      }
	   },
	   labels: {
	      style: {
	         color: '#707073'
	      }
	   },

	   drilldown: {
	      activeAxisLabelStyle: {
	         color: '#F0F0F3'
	      },
	      activeDataLabelStyle: {
	         color: '#F0F0F3'
	      }
	   },

	   navigation: {
	      buttonOptions: {
	         symbolStroke: '#DDDDDD',
	         theme: {
	            fill: '#505053'
	         }
	      }
	   },

	   // scroll charts
	   rangeSelector: {
	      buttonTheme: {
	         fill: '#505053',
	         stroke: '#000000',
	         style: {
	            color: '#CCC'
	         },
	         states: {
	            hover: {
	               fill: '#707073',
	               stroke: '#000000',
	               style: {
	                  color: 'white'
	               }
	            },
	            select: {
	               fill: '#000003',
	               stroke: '#000000',
	               style: {
	                  color: 'white'
	               }
	            }
	         }
	      },
	      inputBoxBorderColor: '#505053',
	      inputStyle: {
	         backgroundColor: '#333',
	         color: 'silver'
	      },
	      labelStyle: {
	         color: 'silver'
	      }
	   },

	   navigator: {
	      handles: {
	         backgroundColor: '#666',
	         borderColor: '#AAA'
	      },
	      outlineColor: '#CCC',
	      maskFill: 'rgba(255,255,255,0.1)',
	      series: {
	         color: '#7798BF',
	         lineColor: '#A6C7ED'
	      },
	      xAxis: {
	         gridLineColor: '#505053'
	      }
	   },

	   scrollbar: {
	      barBackgroundColor: '#808083',
	      barBorderColor: '#808083',
	      buttonArrowColor: '#CCC',
	      buttonBackgroundColor: '#606063',
	      buttonBorderColor: '#606063',
	      rifleColor: '#FFF',
	      trackBackgroundColor: '#404043',
	      trackBorderColor: '#404043'
	   },

	   // special colors for some of the
	   legendBackgroundColor: 'rgba(0, 0, 0, 0.5)',
	   background2: '#505053',
	   dataLabelsColor: '#B0B0B3',
	   textColor: '#C0C0C0',
	   contrastTextColor: '#F0F0F3',
	   maskColor: 'rgba(255,255,255,0.3)'
	};

	// Apply the theme
	Highcharts.setOptions(Highcharts.theme);


	// Highcharts.setOptions({colors: ['#69cd8e', '#f45b5b', '#f7a35c', '#aaa6a6', '#64E572', '#FF9655', '#FFF263', '#6AF9C4']});
	// with drilldown
	$('#pie-drilldown').highcharts({
	chart: {
			plotBackgroundColor: null,
			plotBorderWidth: null,
			plotShadow: false,
			type: 'pie'
		},
		title: {
			text: 'Accounts State'
		},
		subtitle: {
			text: "Click the slices to view the authentication methods of each category"
		},
		tooltip: {
			headerFormat: '<span>{point.key} Accounts</span><br/>',
			pointFormat: 'Population: {point.num}'
		},
		plotOptions: {
			pie: {
				allowPointSelect: true,
				cursor: 'pointer',
				dataLabels: {
					enabled: true,
					format: '<b>{point.name}: {point.percentage:.1f} %</b>',
					style: {
						colors: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
					}
				}
			}
		},
		series: [{
			// type: 'column',
			name: 'Accounts' ,
			data: 
				[{
					name: 'Active',
					y: 63.2,
					// sliced: true,
					// selected: true,
					num: 3000,
					drilldown: 'providers-act',
					// color: '#69cd8e'
				},
				{
					name: 'Inactive',
					y:   2.4,
					drilldown: 'providers-inact',
					num: 100,
				},
				{
					name: 'Pending Moderation',
					y: 27.1,
					num: 700,
					drilldown: 'providers-pMod'
				},
				{
					name: 'Pending Verification',
					y: 7.3,
					num: 300,
					drilldown: 'providers-pVer'
				}]
		}],
		drilldown: {
			series: 
				[{
					id: 'providers-act',
					type: 'column',
					data: [
						{
							name: 'Shibboleth',
							y: 60, // percentage is per parent-slice (60% of active accounts are shibboleth)

						},
						{
							name: 'Local',
							y: 40,
							color: '#839dd6'
						}]
				},
				{
					id: 'providers-inact',
					data: [
						{
							name: 'Shibboleth',
							y: 10
						},
						{
						name: 'Local',
						y: 90,
						color: '#839dd6'
						}]
				},
				{
					id: 'providers-pMod',
					data: [
						{
							name: 'Shibboleth',
							y: 0
						},
					{
						name: 'Local',
						y: 100,
						color: '#839dd6'
					}]
				},
				{
					id: 'providers-pVer',
					data: [
						{
							name: 'Shibboleth',
							y: 20
						},
						{
							name: 'Local',
							y: 80,
							color: '#839dd6'
						}]
				}]
		}
	});




$('#pie-simple').highcharts({
	chart: {
			plotBackgroundColor: null,
			plotBorderWidth: null,
			plotShadow: false,
			type: 'pie'
		},
		title: {
			text: 'Servers Status'
		},
		subtitle: {
			text: "Data Last update: 12/12/2012 01.00"
		},
		tooltip: {
			headerFormat: '<span>{point.key} Servers</span><br/>',
			pointFormat: 'Population: {point.num}'
		},
		plotOptions: {
			pie: {
				allowPointSelect: true,
				cursor: 'pointer',
				dataLabels: {
					enabled: true,
					format: '<b>{point.name}: {point.percentage:.1f} %</b>',
					style: {
						colors: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
					}
				}
			}
		},
		series: [{
			// type: 'pie',
			name: 'Servers' ,
			data: 
				[{
					name: 'Started',
					y: 45,
					// sliced: true,
					// selected: true,
					num: 2250
				},
				{
					name: 'Error',
					y:   5,
					num: 250,
				},
				{
					name: 'Stopped',
					y: 50,
					num: 2500,
					color: '#858585'
				}]
		}]
	});


	/*
	Notes:
	- the series.data should be placed in this order so each pie-slice to have the right color (eg active <- green)
	- I want the tooltip to have the raw number of population se I added "property"
	- The plan is to create series.data form the accountsData func that will take as parameter an array of objs like accounts
	*/
	//     function accountsData() {

	//     }
	//     var accounts = [
	//     {
	//     	state: 'Active',
	//     	population: 1000,
	//     	percentage: 0
	//     },
	//     {
	//     	state: 'Inactive',
	//     	population: 10,
	//     	percentage: 0
	//     },
	//     {
	//     	state: 'Pending Verification',
	//     	population: 300,
	//     	percentage: 0
	//     },
	//     {
	//     	state: 'Pending Moderation',
	//     	population: 700,
	//     	percentage: 0
	//     }]


		$('#timeline1').highcharts('StockChart', {
			rangeSelector : {
				selected : 3,
				inputEnabled: $('#timeline1').width() > 480
			},
			yAxis: {
				// title: {
				// 	text: 'Activated Users'
				// },
			// 	// opposite: true,
				lineWidth: 1,
				tickWidth: 1,
				// offset: 20,
				labels: {
					align: 'left',
					x: 18,
					y: 3
				}
			},
			// xAxis: [{

			// 	lineWidth: 2,
			// 	tickWidth: 2
			// }],
			title : {
				text : 'Demo Zoomable Timeline'
			},
			series : [{
				name : 'demo',
				data : timelineArray,
				tooltip: {
					valueDecimals: 2
				}
			}]
		});
		$('#timeline2').highcharts('StockChart', {
			rangeSelector : {
				selected : 0,
				inputEnabled: $('#timeline2').width() > 480
			},
			title : {
				text : 'Demo Zoomable Timeline'
			},
			series : [{
				name : 'demo',
				data : timelineArray,
				marker : {
					enabled : true,
					radius : 3
				},
				shadow : true,
				tooltip: {
					valueDecimals: 2
				}
			}]
		});
		$('#timeline3').highcharts('StockChart', {
			rangeSelector : {
				selected : 4,
				inputEnabled: $('#timeline3').width() > 480
			},
			title : {
				text : 'Demo Zoomable Timeline'
			},
			series : [{
				name : 'demo',
				data : timelineArray,
				type: 'area',
				threshold : null,
				// marker : {
					// enabled : true,
					// radius : 3
				// },
				// shadow : true,
				tooltip: {
					valueDecimals: 2
				},
				fillColor : {
					linearGradient : {
						x1: 0,
						y1: 0,
						x2: 0,
						y2: 1
					},
					stops : [
						[0, Highcharts.getOptions().colors[7]],
						[1, Highcharts.Color(Highcharts.getOptions().colors[3]).setOpacity(0).get('rgba')]
					]
				}
			}]
		});
		$('#timeline4').highcharts({
            chart: {
                zoomType: 'xy'
            },
            title: {
                text: 'Demo Alternative Way to Zoom'
            },
            subtitle: {
                text: document.ontouchstart === undefined ?
                    'Click and drag in the plot area to zoom in' :
                    'Pinch the chart to zoom in'
            },
            xAxis: {
                type: 'datetime',
                minRange: 14 * 24 * 3600000 // fourteen days
            },
            yAxis: {
                title: {
                    text: 'Blah Blah'
                },
                // opposite: true // here is working just fine
            },
            legend: {
                enabled: false
            },
            plotOptions: {
                area: {
                    fillColor: {
                        linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1},
                        stops: [
                            [0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                        ]
                    },
                    marker: {
                        radius: 2
                    },
                    lineWidth: 1,
                    states: {
                        hover: {
                            lineWidth: 1
                        }
                    },
                    threshold: null
                }
            },

            series: [{
                type: 'area',
                name: 'Demo',
                data: timelineArray
            }]
        });

	$('#columnchart').highcharts({
            chart: {
                type: 'column'
            },
            title: {
                text: 'VMs per disk'
            },
            // subtitle: {
            //     text: ''
            // },
            xAxis: {
                categories: [
                    'Jan',
                    'Feb',
                    'Mar',
                    'Apr',
                    'May',
                    'Jun',
                    'Jul',
                    'Aug',
                    'Sep',
                    'Oct',
                    'Nov',
                    'Dec'
                ]
            },
            yAxis: {
                min: 0,
                title: {
                    text: 'Number of VMs'
                }
            },
            tooltip: {
                headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
                pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                    '<td style="padding:0"><b>{point.y:.1f} mm</b></td></tr>',
                footerFormat: '</table>',
                shared: true,
                useHTML: true
            },
            plotOptions: {
                column: {
                    pointPadding: 0.2,
                    borderWidth: 0,
                    pointWidth: 20
                }
            },
            series: [{
                name: '100GB',
                data: [49.9, 71.5, 106.4, 129.2, 144.0, 176.0, 135.6, 148.5, 216.4, 194.1, 95.6, 54.4]
            }, {
                name: '30GB',
                data: [83.6, 78.8, 98.5, 93.4, 106.0, 84.5, 105.0, 104.3, 91.2, 83.5, 106.6, 92.3]
            }, {
                name: '20GB',
                data: [48.9, 38.8, 39.3, 41.4, 47.0, 48.3, 59.0, 59.6, 52.4, 65.2, 59.3, 51.2]
            }, {
                name: '5GB',
                data: [42.4, 33.2, 34.5, 39.7, 52.6, 75.5, 57.4, 60.4, 47.6, 39.1, 46.8, 51.1]
            }]
        });

});
