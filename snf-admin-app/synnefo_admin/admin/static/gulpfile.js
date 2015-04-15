var gulp = require('gulp');
var compass = require('gulp-for-compass');

// minimist is used in order to extract easily cli params
var minimist = require('minimist');
var newer = require('gulp-newer');

// Reconsider to modify the format of the path
var path_share = '../../../../../../usr/share/synnefo/static/admin/';
var custom_options= {
  string: 'output',
  default: { output: process.env.NODE_ENV || path_share}
}

var options = minimist(process.argv.slice(2), custom_options);

var output_css = options.output + 'css';
var input_css_lib = 'styles/css/lib/*';
var input_sass = ['styles/sass/*.scss', 'styles/sass/*/*.scss'];
var input_sass_dir = 'styles/sass';

var output_js = options.output + 'js';
var input_js = 'js/*/*.js';

var input_images = 'images/*';
var output_images = options.output + 'images';

var input_fonts = 'fonts/*';
var output_fonts = options.output + 'fonts'

gulp.task('compass', function() {
  return gulp.src(input_sass)
    .pipe(newer(output_css))
    .pipe(compass({
      sassDir: input_sass_dir,
      cssDir: output_css
    }));
});

gulp.task('copy', function(){
  gulp.src(input_css_lib)
    .pipe(newer(output_css))
    .pipe(gulp.dest(output_css));
  gulp.src(input_js)
    .pipe(newer(output_js))
    .pipe(gulp.dest(output_js));
  gulp.src(input_images)
    .pipe(newer(output_images))
    .pipe(gulp.dest(output_images));
  gulp.src(input_fonts)
    .pipe(newer(output_fonts))
  .pipe(gulp.dest(output_fonts));
});

gulp.task('default', ['copy', 'compass'], function() {

  gulp.watch(input_sass, ['compass']);
  gulp.watch([input_css_lib, input_js, input_images, input_fonts], ['copy']);

});

