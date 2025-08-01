var autoprefixer = require('autoprefixer');
var gulp = require('gulp');
var concat = require('gulp-concat');
var cssnano = require('cssnano');
var order = require('gulp-order');
var path = require('path');
var plumber = require('gulp-plumber');
var postcss = require('gulp-postcss');
var sass = require('gulp-sass')(require('sass'));
var uglify = require('gulp-uglify');

const { series } = require('gulp');

function move_css() {
    return gulp.src([
        'node_modules/tabulator-tables/dist/css/tabulator_bootstrap5.min.css',
	], {"allowEmpty": true})
	.pipe(gulp.dest('apps/common/src/vendor-css'))
}

function move_js() {
    return gulp.src([
        'node_modules/tabulator-tables/dist/js/tabulator.min.js',
        'node_modules/sortablejs/Sortable.min.js',
	], {"allowEmpty": true})
	.pipe(gulp.dest('apps/common/src/vendor-js'))
}

function move_icons() {
	return gulp.src([
	    'node_modules/bootstrap-icons/font/bootstrap-icons.min.css',
	], {"allowEmpty": true})
	.pipe(gulp.dest('apps/common/dist/'));
}

function move_fonts() {
	return gulp.src([
        'node_modules/bootstrap-icons/font/fonts/*',
	], {"allowEmpty": true})
	.pipe(gulp.dest('apps/common/dist/fonts'));
}

function img() {
    return gulp.src('apps/common/src/img/**/*')
	.pipe(gulp.dest('apps/common/dist/images/'));
}

function move_alpine_js() {
    return gulp.src('node_modules/alpinejs/dist/cdn.min.js')
	.pipe(gulp.dest('apps/common/dist/'));
}

function js() {
	return gulp.src(['apps/common/src/js/**/*.js'])
	.pipe(plumber())
	.pipe(uglify())
	.pipe(concat('script.min.js'))
	.pipe(gulp.dest('apps/common/dist/'));
}

function scss() {
    return gulp.src(['apps/common/src/scss/style.scss'])
	.pipe(plumber())
	.pipe(sass())
	.pipe(postcss([autoprefixer(), cssnano()]))
	.pipe(concat('style.min.css'))
	.pipe(gulp.dest('apps/common/dist/'));
}

function vendor_js() {
	return gulp.src('apps/common/src/vendor-js/*.js')
	.pipe(plumber())
	.pipe(order([
		"apps/common/src/vendor-js/*.js"
	], { base: __dirname }))
	.pipe(concat('vendor.min.js'))
	.pipe(uglify())
	.pipe(gulp.dest('apps/common/dist/'));
}

function vendor_css() {
	return gulp.src('apps/common/src/vendor-css/*.css')
	.pipe(plumber())
	.pipe(postcss([autoprefixer(), cssnano()]))
	.pipe(concat('vendor.min.css'))
	.pipe(gulp.dest('apps/common/dist/'));
}

exports.move_css = move_css;
exports.move_js = move_js;
exports.move_icons = move_icons;
exports.move_fonts = move_fonts
exports.move_alpine_js = move_alpine_js
exports.move = series(move_css, move_js, move_icons, move_fonts, move_alpine_js);

exports.img = img;
exports.js = js;
exports.scss = scss;
exports.vendor_css = vendor_css;
exports.vendor_js = vendor_js;
exports.default = series(img, js, scss, vendor_css, vendor_js);

gulp.task('serve', function () {
	gulp.watch('apps/common/src/img/**/*', gulp.series('img'));
	gulp.watch(['apps/common/src/js/**/*.js'], gulp.series('js'));
	gulp.watch(['apps/common/src/scss/*.scss', 'apps/common/src/scss/*/*.scss'], gulp.series('scss'));
	gulp.watch('apps/common/src/vendor-css/*.css', gulp.series('vendor_css'));
	gulp.watch('apps/common/src/vendor-js/*.js', gulp.series('vendor_js'));
});